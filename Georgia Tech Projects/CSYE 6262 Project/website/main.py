
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .database import candidates, count_products, get_product, search_products
from .attributes import compare_attributes
from .feedback import save_feedback
from .registry import ModelUnavailable, entries, model_entry, model_info, predict_pairs


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Product Matching API",
    description="Product matching with selectable SVM and Random Forest models",
    version="2.0.0"
)

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)


class Product(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)
    title: str = Field(min_length=1, max_length=2000)
    brand: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=12000)
    price: float | None = Field(default=None, ge=0, le=1e9)
    currency: str = Field(default="USD", max_length=30)
    seller: str = Field(default="", max_length=300)
    source_id: str | None = Field(default=None, max_length=300)
    category: str | None = Field(default=None, max_length=300)
    specTableContent: str = Field(default="", max_length=12000)


class ProductPair(BaseModel):
    product_a: Product
    product_b: Product
    model_id: str | None = Field(default=None, max_length=100)


class Batch(BaseModel):
    model_id: str | None = Field(default=None, max_length=100)
    pairs: list[ProductPair] = Field(min_length=1, max_length=50)


class Feedback(ProductPair):
    choice: Literal["match", "different", "unsure"]
    request_id: UUID
    model_id: str = Field(min_length=1, max_length=100)
    model_version: str = Field(min_length=1, max_length=100)


def prediction(a, b, model_id=None):
    return predictions([(a, b)], model_id)[0]


def predictions(pairs, model_id=None):
    try:
        return predict_pairs(pairs, model_id)
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=503, detail="Model prediction failed. Check the server's artifact compatibility.")


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/live")
def live():
    return {"status": "running"}


@app.get("/health")
def health():
    info = model_info()
    if not info["available"]:
        raise HTTPException(status_code=503, detail=info["message"])
    return {"status": "healthy", "model": info["name"], "model_loaded": True,
            "indexed_products": count_products()}


@app.get("/search")
def search(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=20, ge=1, le=50)
):
    try:
        results = search_products(q, limit)

        return {
            "query": q,
            "count": len(results),
            "results": results
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {exc}"
        )


@app.post("/predict")
def predict(pair: ProductPair):
    a, b = pair.product_a.model_dump(), pair.product_b.model_dump()
    result = prediction(a, b, pair.model_id)
    result["attributes"] = compare_attributes(a, b)
    if (result["is_match"] and a["price"] is not None and b["price"] is not None
            and a["currency"] and a["currency"].upper() == b["currency"].upper()):
        result["price_comparison"] = {
            "price_difference": round(abs(a["price"] - b["price"]), 2),
            "cheaper_product": "Same price" if a["price"] == b["price"] else (
                "Product A" if a["price"] < b["price"] else "Product B"),
            "currency": a["currency"].upper(),
        }
    return result


def display_model_info(entry):
    info = model_info(entry)
    if entry["adapter"] in {"logistic_pair_v1", "random_forest_pair_v1"}:
        # Keep prediction capabilities, but do not publish evaluation records or notes.
        info.pop("evaluation", None)
        info["integration_note"] = "The supplied training code uses computers only."
    return info


@app.get("/models")
def models():
    return {"active_model": model_entry()["id"], "models": [display_model_info(entry) for entry in entries() if entry.get("show_in_website", True)]}


@app.get("/candidates/{product_id}")
def product_candidates(product_id: int, limit: int = Query(default=40, ge=1, le=50),
                       model_id: str | None = Query(default=None, max_length=100)):
    reference = get_product(product_id)
    if reference is None:
        raise HTTPException(status_code=404, detail="Reference product not found.")
    products = candidates(reference, limit)
    try:
        info = display_model_info(model_entry(model_id))
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    results = predictions([(reference, item) for item in products], model_id) if products and info["available"] else [None] * len(products)
    return {"reference": reference, "model": info,
            "retrieval": "Top lexical candidates; not an exhaustive search or verified matches.",
            "candidates": [{"product": item, "prediction": result} for item, result in zip(products, results)]}


@app.post("/predict/batch")
def batch_predict(batch: Batch):
    pairs = [(pair.product_a.model_dump(), pair.product_b.model_dump()) for pair in batch.pairs]
    return {"results": predictions(pairs, batch.model_id)}


@app.post("/compare")
def compare(pair: ProductPair):
    return {"attributes": compare_attributes(pair.product_a.model_dump(), pair.product_b.model_dump())}


@app.post("/feedback")
def feedback(item: Feedback):
    a, b = item.product_a.model_dump(), item.product_b.model_dump()
    result = prediction(a, b, item.model_id)  # Original prediction comes from the server, never the browser.
    if result["model_id"] != item.model_id or result["model_version"] != item.model_version:
        raise HTTPException(status_code=409, detail="The active model changed. Run a new official prediction before reviewing it.")
    try:
        return save_feedback(a, b, result, item.choice, str(item.request_id))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/evaluation")
def evaluation():
    # Versioned, team-reviewed metrics only. No inferred metrics from search results.
    return {"models": [{"id": entry["id"], "name": entry["name"], "version": entry["version"],
                        "evaluation": entry.get("evaluation"),
                        "integration_note": entry.get("integration_note")} for entry in entries() if entry.get("show_in_website", True)
                        and entry["adapter"] not in {"logistic_pair_v1", "random_forest_pair_v1"}]}
