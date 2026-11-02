
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .database import count_products, search_products
from .model import load_model, predict_match


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Product Matching API",
    description="SVM product matching and product search",
    version="2.0.0"
)

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)


class Product(BaseModel):
    title: str = Field(min_length=1)
    brand: str = ""
    description: str = ""
    price: float | None = Field(default=None, ge=0)


class ProductPair(BaseModel):
    product_a: Product
    product_b: Product


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/live")
def live():
    return {"status": "running"}


@app.get("/health")
def health():
    try:
        load_model()

        return {
            "status": "healthy",
            "model": "SVM Version 3",
            "model_loaded": True,
            "indexed_products": count_products()
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc)
        )


@app.get("/search")
def search(
    q: str = Query(min_length=2),
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
    try:
        return predict_match(
            pair.product_a,
            pair.product_b
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {exc}"
        )
