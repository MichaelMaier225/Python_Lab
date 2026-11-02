
const get = id => document.getElementById(id);

const form = get("compare-form");
const result = get("result");
const error = get("error");
const compareBtn = get("compare-btn");


// Read information from either product form
function getProduct(prefix) {
    const rawPrice = get(`${prefix}-price`).value.trim();

    return {
        title: get(`${prefix}-title`).value.trim(),
        brand: get(`${prefix}-brand`).value.trim(),
        description: get(`${prefix}-description`).value.trim(),
        price: rawPrice === "" ? null : Number(rawPrice)
    };
}


// Compare products using the trained SVM
form.addEventListener("submit", async event => {
    event.preventDefault();

    error.hidden = true;
    result.hidden = true;

    compareBtn.disabled = true;
    get("btn-text").textContent = "Comparing...";

    try {
        const response = await fetch("/predict", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                product_a: getProduct("a"),
                product_b: getProduct("b")
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                typeof data.detail === "string"
                    ? data.detail
                    : "Prediction failed"
            );
        }

        result.className = data.is_match
            ? "panel result match"
            : "panel result nonmatch";

        get("result-title").textContent = data.is_match
            ? "Likely the Same Product"
            : "Likely Different Products";

        get("result-pill").textContent = data.is_match
            ? "MATCH"
            : "NO MATCH";

        get("result-explanation").textContent = data.is_match
            ? "The SVM predicts that these listings refer to the same product."
            : "The SVM predicts that these listings refer to different products.";

        get("decision-score").textContent =
            Number(data.decision_score).toFixed(4);

        get("threshold").textContent =
            Number(data.threshold).toFixed(2);

        const priceResult = get("price-result");

        if (data.price_comparison) {
            const price = data.price_comparison;

            const amount = Number(
                price.price_difference
            ).toFixed(2);

            get("price-message").textContent =
                price.cheaper_product === "Same price"
                    ? "Both products have the same price."
                    : `${price.cheaper_product} is cheaper by $${amount}.`;

            priceResult.hidden = false;
        } else {
            priceResult.hidden = true;
        }

        result.hidden = false;

        result.scrollIntoView({
            behavior: "smooth",
            block: "nearest"
        });

    } catch (err) {
        error.textContent = err.message;
        error.hidden = false;

    } finally {
        compareBtn.disabled = false;
        get("btn-text").textContent = "Compare Products";
    }
});


// Fill the comparison form with an example
get("example-btn").addEventListener("click", () => {
    const example = {
        "a-title": "Samsung 990 PRO 1TB NVMe SSD",
        "a-brand": "Samsung",
        "a-description": "Samsung 990 PRO 1TB PCIe 4.0 SSD",
        "a-price": "109.99",

        "b-title": "Samsung 990 PRO 1TB PCIe SSD",
        "b-brand": "Samsung",
        "b-description": "Samsung 990 PRO 1TB NVMe solid state drive",
        "b-price": "119.99"
    };

    Object.entries(example).forEach(([id, value]) => {
        get(id).value = value;
    });

    result.hidden = true;
    error.hidden = true;
});


// Clear the comparison form
get("clear-btn").addEventListener("click", () => {
    form.reset();
    result.hidden = true;
    error.hidden = true;
});


// Copy a database listing into Product A or B
function fillProduct(prefix, item) {
    get(`${prefix}-title`).value = item.title || "";
    get(`${prefix}-brand`).value = item.brand || "";
    get(`${prefix}-description`).value =
        item.description || "";

    // Compare prices only when the currency is known to be USD.
    const isUSD = (item.currency || "").toUpperCase() === "USD";

    get(`${prefix}-price`).value =
        item.price !== null && isUSD
            ? item.price
            : "";

    result.hidden = true;
    error.hidden = true;

    get(`${prefix}-title`).scrollIntoView({
        behavior: "smooth",
        block: "center"
    });
}


// Format historical product prices
function formatPrice(price, currency) {
    if (price === null || price === undefined) {
        return "Price unavailable";
    }

    const code = (currency || "").toUpperCase();

    if (code === "USD") {
        return `$${Number(price).toFixed(2)}`;
    }

    if (code) {
        return `${Number(price).toFixed(2)} ${code}`;
    }

    return `${Number(price).toFixed(2)} (currency unknown)`;
}


// Search WDC products
get("search-form").addEventListener("submit", async event => {
    event.preventDefault();

    const query = get("search-query").value.trim();
    const status = get("search-status");
    const results = get("search-results");

    results.replaceChildren();
    status.textContent = "Searching...";

    try {
        const response = await fetch(
            `/search?q=${encodeURIComponent(query)}&limit=20`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                typeof data.detail === "string"
                    ? data.detail
                    : "Search failed"
            );
        }

        status.textContent =
            `${data.count} product listings found.`;

        if (data.count === 0) {
            status.textContent =
                "No products found. Try a different search.";
            return;
        }

        for (const item of data.results) {

            const row = document.createElement("div");
            row.className = "search-item";

            const details = document.createElement("div");

            const title = document.createElement("h3");
            title.textContent = item.title;

            const info = document.createElement("p");
            info.textContent = [
                item.brand,
                item.seller,
                formatPrice(item.price, item.currency)
            ].filter(Boolean).join(" | ");

            details.append(title, info);

            if (
                item.url &&
                /^https?:\/\//i.test(item.url)
            ) {
                const link = document.createElement("a");
                link.href = item.url;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.textContent = "View original listing";

                details.append(link);
            }

            const actions = document.createElement("div");
            actions.className = "search-item-actions";

            const buttonA = document.createElement("button");
            buttonA.type = "button";
            buttonA.textContent = "Use as A";

            buttonA.addEventListener("click", () => {
                fillProduct("a", item);
            });

            const buttonB = document.createElement("button");
            buttonB.type = "button";
            buttonB.textContent = "Use as B";

            buttonB.addEventListener("click", () => {
                fillProduct("b", item);
            });

            actions.append(buttonA, buttonB);
            row.append(details, actions);

            results.append(row);
        }

    } catch (err) {
        status.textContent = `Search failed: ${err.message}`;
    }
});
