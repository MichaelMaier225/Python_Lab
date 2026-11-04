const get = (id) => document.getElementById(id);
const state = {
    reference: null,
    candidates: [],
    selected: null,
    model: null,
    reviewed: null,
    requestId: null,
    evaluation: [],
    referenceRequest: 0,
    pairRequest: 0,
    listings: {}
};

function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
}

async function api(path, body) {
    const response = await fetch(
        path,
        body === undefined
            ? {}
            : {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(body)
              }
    );
    let data;
    try {
        data = await response.json();
    } catch {
        throw new Error("The server returned an unexpected response. Please try again.");
    }
    if (!response.ok)
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Check the product fields and try again."
        );
    return data;
}

function price(product) {
    return product.price === null || product.price === undefined
        ? "Price unavailable"
        : `${Number(product.price).toFixed(2)} ${product.currency || "(currency unknown)"}`;
}

function feedbackEnabled(enabled) {
    document.querySelectorAll("[data-choice]").forEach((button) => {
        button.disabled = !enabled;
    });
}

function invalidatePair() {
    state.pairRequest++;
    state.reviewed = null;
    state.requestId = null;
    feedbackEnabled(false);
    get("pair-result").hidden = true;
    get("pair-error").hidden = true;
    get("attribute-body").replaceChildren();
    get("attribute-summary").textContent = "Compare this pair to see attribute agreement.";
    get("feedback-status").textContent = "Run a prediction to submit a review.";
}

function fillProduct(prefix, product) {
    state.listings[prefix] = product;
    get(`${prefix}-summary`).textContent =
        product.title ||
        (prefix === "a" ? "Choose a reference listing" : "Select a candidate to compare");
    for (const field of ["title", "brand", "description", "price", "currency"]) {
        get(`${prefix}-${field}`).value = product[field] ?? "";
    }
}

function getProduct(prefix) {
    const raw = get(`${prefix}-price`).value.trim();
    return {
        title: get(`${prefix}-title`).value.trim(),
        brand: get(`${prefix}-brand`).value.trim(),
        description: get(`${prefix}-description`).value.trim(),
        price: raw === "" ? null : Number(raw),
        currency: get(`${prefix}-currency`).value.trim().toUpperCase(),
        seller: state.listings[prefix]?.seller || "",
        source_id: state.listings[prefix]?.source_id || null,
        category: state.listings[prefix]?.category || null
    };
}

function pair() {
    return { product_a: getProduct("a"), product_b: getProduct("b") };
}

function showError(message) {
    get("pair-error").textContent = message;
    get("pair-error").hidden = false;
}

function showModel(info) {
    state.model = info;
    const status = get("model-status");
    status.className = info.available ? "model-status" : "model-status warning";
    status.textContent = `${info.name} · version ${info.version} — ${
        info.available
            ? "Ready. " +
              (info.capabilities.probability
                  ? "Probability output."
                  : "Scores are not probabilities.")
            : info.message + " You can still compare attributes manually."
    }`;
    get("compare-btn").disabled = !info.available;
}

function populateFilter(id, values, label) {
    const select = get(id);
    select.replaceChildren(new Option(label, ""));
    [...new Set(values.filter(Boolean))]
        .sort()
        .forEach((value) => select.add(new Option(value, value)));
}

function setThreshold() {
    const flags = state.model?.capabilities;
    const slider = get("threshold");
    slider.disabled = !flags?.threshold;
    get("threshold-box").hidden = !flags?.threshold || !state.reference;
    if (!flags?.threshold) {
        get("threshold-value").textContent = "Unavailable";
        return;
    }
    const base = flags.default_threshold;
    const scores = state.candidates
        .map((item) => item.prediction?.raw_score)
        .filter(Number.isFinite);
    slider.min = flags.probability ? 0 : Math.min(base - 1, ...scores);
    slider.max = flags.probability ? 1 : Math.max(base + 1, ...scores);
    slider.step = "any";
    slider.value = base;
}

function matches(item) {
    if (!item.prediction) return null;
    if (!get("threshold").disabled && Number.isFinite(item.prediction.raw_score)) {
        const cutoff = Number(get("threshold").value);
        if (cutoff === item.prediction.threshold) return item.prediction.is_match;
        return item.prediction.raw_score >= cutoff;
    }
    return item.prediction.is_match;
}

function visibleCandidates() {
    const vendor = get("vendor-filter").value,
        currency = get("currency-filter").value;
    const status = get("match-filter").value;
    const min = get("min-price").value,
        max = get("max-price").value;
    const items = state.candidates.filter((item) => {
        const product = item.product,
            match = matches(item);
        return (
            (!vendor || (product.seller || "Unknown vendor") === vendor) &&
            (!currency || (product.currency || "").toUpperCase() === currency) &&
            (!status ||
                (status === "unscored"
                    ? match === null
                    : match !== null && match === (status === "match"))) &&
            (!currency || min === "" || (product.price !== null && product.price >= Number(min))) &&
            (!currency || max === "" || (product.price !== null && product.price <= Number(max)))
        );
    });
    const sort = get("sort-filter").value;
    if (sort === "score")
        items.sort(
            (a, b) =>
                (b.prediction?.raw_score ?? -Infinity) - (a.prediction?.raw_score ?? -Infinity)
        );
    if (sort === "price" && currency)
        items.sort((a, b) => (a.product.price ?? Infinity) - (b.product.price ?? Infinity));
    return items;
}

function renderCandidates() {
    const currency = get("currency-filter").value;
    const hasReference = Boolean(state.reference);
    get("candidate-empty").hidden = hasReference;
    get("candidate-chart").hidden = !hasReference;
    get("chart-context").hidden = !hasReference;
    get("candidate-filters").disabled = !state.candidates.length;
    get("min-price").disabled = !currency;
    get("max-price").disabled = !currency;
    get("sort-filter").querySelector('option[value="price"]').disabled = !currency;
    const items = visibleCandidates();
    get("visible-count").textContent = items.length;
    get("match-count").textContent = state.model?.available
        ? items.filter((item) => matches(item) === true).length
        : "—";
    const eligible = items.filter(
        (item) => matches(item) === true && item.product.price !== null && currency
    );
    get("lowest-price").textContent = eligible.length
        ? price(eligible.reduce((a, b) => (a.product.price < b.product.price ? a : b)).product)
        : "—";
    if (!get("threshold").disabled) {
        get("threshold-value").textContent = Number(get("threshold").value).toFixed(4);
        get("threshold-note").textContent =
            `Official default: ${state.model.capabilities.default_threshold}. This slider changes exploration only.`;
    }
    get("candidate-status").textContent = state.candidates.length
        ? `${items.length} of ${state.candidates.length} listings · select a point or Inspect`
        : state.reference
          ? "No candidates found for this reference."
          : "Waiting for a reference product.";
    const list = get("candidate-list");
    list.replaceChildren();
    for (const item of items) {
        const row = node(
            "div",
            undefined,
            "candidate-row" + (state.selected === item.product.id ? " selected" : "")
        );
        const content = node("div");
        content.append(node("strong", item.product.title));
        const match = matches(item);
        content.append(
            node(
                "p",
                `${item.product.seller || "Unknown vendor"} · ${price(item.product)} · ${match === null ? "Unscored" : match ? "Match" : "Different"}${Number.isFinite(item.prediction?.raw_score) ? " · score " + item.prediction.raw_score.toFixed(4) : ""}`,
                "muted"
            )
        );
        const button = node("button", "Inspect", "secondary");
        button.type = "button";
        button.addEventListener("click", () => selectCandidate(item));
        row.append(content, button);
        list.append(row);
    }
    if (!hasReference) {
        get("candidate-chart").replaceChildren();
        return;
    }
    drawCandidates(items, {
        currency,
        selected: state.selected,
        scoreType: state.model?.capabilities?.score_type,
        threshold: get("threshold").disabled ? null : Number(get("threshold").value),
        isMatch: matches,
        select: selectCandidate
    });
}

function renderAttributes(rows) {
    const body = get("attribute-body");
    body.replaceChildren();
    for (const row of rows) {
        const tr = node("tr");
        tr.append(
            node("th", row.attribute),
            node("td", row.a || "Unknown"),
            node("td", row.b || "Unknown"),
            node(
                "td",
                row.status === "match"
                    ? "Match"
                    : row.status === "conflict"
                      ? "Conflict"
                      : "Unknown",
                `status-${row.status}`
            )
        );
        body.append(tr);
    }
    get("attribute-summary").textContent =
        `${rows.filter((row) => row.status === "match").length} matching · ${rows.filter((row) => row.status === "conflict").length} conflicting · ${rows.filter((row) => row.status === "unknown").length} unknown.`;
}

async function compareAttributes() {
    if (!get("compare-form").reportValidity()) return;
    const request = ++state.pairRequest;
    try {
        const data = await api("/compare", pair());
        if (request === state.pairRequest) renderAttributes(data.attributes);
    } catch (err) {
        if (request === state.pairRequest) showError(err.message);
    }
}

async function selectCandidate(item) {
    invalidatePair();
    state.selected = item.product.id;
    fillProduct("a", state.reference);
    fillProduct("b", item.product);
    renderCandidates();
    await compareAttributes();
}

async function selectReference(product) {
    const request = ++state.referenceRequest;
    invalidatePair();
    state.reference = product;
    state.selected = null;
    state.candidates = [];
    fillProduct("a", product);
    fillProduct("b", {});
    get("reference-label").textContent = `Reference: ${product.title}`;
    renderCandidates();
    get("candidate-status").textContent = "Retrieving and scoring candidates…";
    try {
        const data = await api(`/candidates/${product.id}`);
        if (request !== state.referenceRequest) return;
        state.candidates = data.candidates;
        showModel(data.model);
        populateFilter(
            "vendor-filter",
            state.candidates.map((item) => item.product.seller || "Unknown vendor"),
            "All vendors"
        );
        populateFilter(
            "currency-filter",
            state.candidates.map((item) => (item.product.currency || "").toUpperCase()),
            "All currencies"
        );
        resetFilters();
    } catch (err) {
        if (request === state.referenceRequest) get("candidate-status").textContent = err.message;
    }
}

function resetFilters() {
    for (const id of ["vendor-filter", "currency-filter", "match-filter", "min-price", "max-price"])
        get(id).value = "";
    get("sort-filter").value = "retrieval";
    setThreshold();
    renderCandidates();
}

get("search-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    get("search-btn").disabled = true;
    get("search-results").replaceChildren();
    get("search-status").textContent = "Searching historical listings…";
    try {
        const data = await api(`/search?q=${encodeURIComponent(get("search-query").value.trim())}`);
        get("search-status").textContent = data.count
            ? `${data.count} listings found. Select a reference to explore.`
            : "No listings found. Try a different brand or model.";
        for (const product of data.results) {
            const card = node("article", undefined, "listing");
            card.append(
                node("h3", product.title),
                node(
                    "p",
                    `${product.brand || "Unknown brand"} · ${product.seller || "Unknown vendor"} · ${price(product)}`,
                    "muted"
                )
            );
            const actions = node("div", undefined, "actions");
            for (const [label, action] of [
                ["Explore matches", () => selectReference(product)],
                [
                    "Use as A",
                    () => {
                        invalidatePair();
                        fillProduct("a", product);
                    }
                ],
                [
                    "Use as B",
                    () => {
                        invalidatePair();
                        fillProduct("b", product);
                    }
                ]
            ]) {
                const button = node(
                    "button",
                    label,
                    label === "Explore matches" ? "" : "secondary"
                );
                button.type = "button";
                button.addEventListener("click", action);
                actions.append(button);
            }
            if (/^https?:\/\//i.test(product.url || "")) {
                const link = node("a", "Original listing");
                link.href = product.url;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                card.append(link);
            }
            card.append(actions);
            get("search-results").append(card);
        }
    } catch (err) {
        get("search-status").textContent = err.message;
    } finally {
        get("search-btn").disabled = false;
    }
});

get("compare-form").addEventListener(
    "invalid",
    () => {
        get("manual-entry").open = true;
    },
    true
);
get("compare-form").addEventListener("input", (event) => {
    const prefix = event.target.id.slice(0, 1);
    delete state.listings[prefix];
    get(`${prefix}-summary`).textContent = get(`${prefix}-title`).value || "No product entered";
    state.selected = null;
    invalidatePair();
    renderCandidates();
});
get("compare-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    invalidatePair();
    const request = ++state.pairRequest;
    const products = pair();
    get("compare-btn").disabled = true;
    get("compare-btn").textContent = "Running prediction…";
    try {
        const data = await api("/predict", products);
        if (request !== state.pairRequest) return;
        renderAttributes(data.attributes);
        const result = get("pair-result");
        let text = `Official prediction: ${data.prediction}. Model ${data.model_id} / ${data.model_version}.`;
        if (data.raw_score !== null)
            text += ` ${data.score_type === "probability" ? "Probability" : "Decision score"}: ${data.raw_score.toFixed(4)}.`;
        if (data.threshold !== null) text += ` Default threshold: ${data.threshold}.`;
        if (data.price_comparison)
            text += ` ${data.price_comparison.cheaper_product}; listed-price difference ${data.price_comparison.price_difference.toFixed(2)} ${data.price_comparison.currency}. Shipping, taxes and condition excluded.`;
        result.textContent = text;
        result.hidden = false;
        state.reviewed = {
            ...products,
            model_id: data.model_id,
            model_version: data.model_version
        };
        state.requestId = crypto.randomUUID();
        feedbackEnabled(true);
        get("feedback-status").textContent = "Ready for your review of the official prediction.";
    } catch (err) {
        if (request === state.pairRequest) showError(err.message);
    } finally {
        get("compare-btn").disabled = !state.model?.available;
        get("compare-btn").textContent = "Run official prediction";
    }
});
get("attributes-btn").addEventListener("click", compareAttributes);
get("clear-btn").addEventListener("click", () => {
    get("compare-form").reset();
    state.listings = {};
    fillProduct("a", {});
    fillProduct("b", {});
    invalidatePair();
    state.selected = null;
    renderCandidates();
});
get("example-btn").addEventListener("click", () => {
    get("manual-entry").open = true;
    invalidatePair();
    fillProduct("a", {
        title: "Samsung 990 PRO 1TB NVMe SSD",
        brand: "Samsung",
        description: "1TB SSD",
        price: 109.99,
        currency: "USD"
    });
    fillProduct("b", {
        title: "Samsung 990 PRO 1TB PCIe SSD",
        brand: "Samsung",
        description: "1TB SSD",
        price: 119.99,
        currency: "USD"
    });
    state.selected = null;
    renderCandidates();
});
for (const id of ["vendor-filter", "currency-filter", "match-filter", "sort-filter"])
    get(id).addEventListener("change", renderCandidates);
for (const id of ["min-price", "max-price", "threshold"])
    get(id).addEventListener("input", renderCandidates);
get("reset-filters").addEventListener("click", resetFilters);

document.querySelectorAll("[data-choice]").forEach((button) =>
    button.addEventListener("click", async () => {
        if (!state.reviewed) return;
        const reviewed = state.reviewed,
            requestId = state.requestId;
        feedbackEnabled(false);
        get("feedback-status").textContent = "Saving your review…";
        try {
            await api("/feedback", {
                ...reviewed,
                request_id: requestId,
                choice: button.dataset.choice
            });
            if (state.requestId === requestId) {
                get("feedback-status").textContent =
                    "Review saved separately from test labels. No model was retrained.";
                state.reviewed = null;
            }
        } catch (err) {
            if (state.requestId === requestId) {
                get("feedback-status").textContent = err.message;
                feedbackEnabled(true);
            }
        }
    })
);

function renderEvaluation() {
    const model = state.evaluation.find((item) => item.id === get("evaluation-model").value);
    const target = get("evaluation-content");
    target.replaceChildren();
    if (model?.integration_note) {
        target.append(node("p", model.integration_note, "notice warning"));
    }
    const data = model?.evaluation;
    if (!data) {
        target.append(
            node(
                "p",
                "No verified evaluation results supplied for this version. Add the original labeled evaluation outputs; no metrics have been invented.",
                "notice warning"
            )
        );
        return;
    }
    target.append(
        node(
            "p",
            `Dataset: ${data.dataset_id || "Not specified"} · split: ${data.split || "Not specified"} · ${data.procedure || "Procedure not documented"}`
        )
    );
    const metrics = node("div", undefined, "metric-grid");
    for (const name of ["accuracy", "precision", "recall", "f1"]) {
        const card = node("div", name.toUpperCase());
        card.append(
            node(
                "strong",
                Number.isFinite(data.metrics?.[name])
                    ? data.metrics[name].toFixed(4)
                    : "Unavailable"
            )
        );
        metrics.append(card);
    }
    target.append(metrics);
    if (data.confusion_matrix) {
        const matrix = node("table");
        const header = node("tr");
        for (const label of ["Actual / predicted", "Different", "Match"])
            header.append(node("th", label));
        matrix.append(header);
        ["Different", "Match"].forEach((label, i) => {
            const row = node("tr");
            row.append(node("th", label));
            data.confusion_matrix[i].forEach((value) => row.append(node("td", String(value))));
            matrix.append(row);
        });
        target.append(node("h3", "Confusion matrix"), matrix);
    }
    if (data.thresholds?.length) {
        const label = node("label", "Explore evaluated thresholds");
        const slider = node("input");
        slider.type = "range";
        slider.min = 0;
        slider.max = data.thresholds.length - 1;
        slider.step = 1;
        slider.value = 0;
        const summary = node("p");
        function update() {
            const point = data.thresholds[Number(slider.value)];
            summary.textContent = `Threshold ${point.threshold} · Precision ${point.precision} · Recall ${point.recall} · FP ${point.fp ?? "unavailable"} · FN ${point.fn ?? "unavailable"}`;
        }
        slider.addEventListener("input", update);
        label.append(slider);
        target.append(label, summary);
        update();
        const chart = node("div", undefined, "chart");
        target.append(chart);
        drawPrecisionRecall(chart, data.thresholds);
    }
    target.append(
        node(
            "p",
            "Version views are not a fair ranking unless dataset, split, labels and evaluation procedure match.",
            "muted"
        )
    );
}
get("evaluation-model").addEventListener("change", renderEvaluation);

function showView(evaluation) {
    get("workspace-view").hidden = evaluation;
    get("evaluation").hidden = !evaluation;
    for (const [id, active] of [
        ["workspace-tab", !evaluation],
        ["evaluation-tab", evaluation]
    ]) {
        get(id).classList.toggle("active", active);
        get(id).setAttribute("aria-pressed", String(active));
    }
}
get("workspace-tab").addEventListener("click", () => showView(false));
document.querySelector(".logo").addEventListener("click", () => showView(false));
get("evaluation-tab").addEventListener("click", () => showView(true));

async function initialize() {
    renderCandidates();
    try {
        const data = await api("/models");
        showModel(data.models.find((item) => item.id === data.active_model));
        setThreshold();
    } catch (err) {
        get("model-status").textContent = err.message;
        get("compare-btn").disabled = true;
    }
    try {
        const data = await api("/evaluation");
        state.evaluation = data.models;
        for (const model of data.models)
            get("evaluation-model").add(new Option(`${model.name} · v${model.version}`, model.id));
        renderEvaluation();
    } catch (err) {
        get("evaluation-content").textContent = err.message;
    }
}
initialize();
