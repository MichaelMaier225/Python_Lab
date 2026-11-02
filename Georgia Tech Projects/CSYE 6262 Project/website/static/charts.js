// D3 v5 is served locally. The candidate list remains usable without the chart.
function drawCandidates(items, options) {
    const target = document.getElementById("candidate-chart");
    target.replaceChildren();
    if (!items.length) {
        target.textContent = "No visible candidates. Select a reference or reset your filters.";
        return;
    }
    if (!window.d3) {
        target.textContent = "Chart library unavailable. Use the candidate list below.";
        return;
    }
    const scored = items.filter((item) => Number.isFinite(item.prediction?.raw_score));
    if (!scored.length) {
        target.textContent =
            "Continuous scores are unavailable. Explore candidates in the linked list below.";
        return;
    }
    const priced = Boolean(options.currency);
    const points = priced ? scored.filter((item) => item.product.price !== null) : scored;
    const omitted = items.length - points.length;
    document.getElementById("chart-note").textContent =
        `${priced ? "X: historical price in " + options.currency : "X: visible candidate position (not a price comparison)"}. Y: ${options.scoreType === "probability" ? "model probability" : "uncalibrated decision score"}. ${omitted} missing-price or unscored listings remain in the list.`;
    if (!points.length) {
        target.textContent =
            "No plottable prices in this currency. The listings remain available below.";
        return;
    }
    const width = 1000,
        height = 340;
    const margin = { left: 70, right: 30, top: 30, bottom: 55 };
    const svg = d3
        .select(target)
        .append("svg")
        .attr("viewBox", `0 0 ${width} ${height}`)
        .attr("role", "group")
        .attr("aria-label", "Select a point to compare its listing");
    const xValue = (item, index) => (priced ? item.product.price : index + 1);
    let xExtent = d3.extent(points, xValue);
    if (xExtent[0] === xExtent[1]) xExtent = [xExtent[0] - 1, xExtent[1] + 1];
    let yValues = points.map((item) => item.prediction.raw_score);
    if (Number.isFinite(options.threshold)) yValues.push(options.threshold);
    let yExtent = d3.extent(yValues);
    if (yExtent[0] === yExtent[1]) yExtent = [yExtent[0] - 0.5, yExtent[1] + 0.5];
    const x = d3
        .scaleLinear()
        .domain(xExtent)
        .nice()
        .range([margin.left, width - margin.right]);
    const y = d3
        .scaleLinear()
        .domain(yExtent)
        .nice()
        .range([height - margin.bottom, margin.top]);
    svg.append("g")
        .attr("transform", `translate(0,${height - margin.bottom})`)
        .call(d3.axisBottom(x).ticks(8));
    svg.append("g").attr("transform", `translate(${margin.left},0)`).call(d3.axisLeft(y).ticks(6));
    svg.append("text")
        .attr("x", width / 2)
        .attr("y", height - 10)
        .attr("text-anchor", "middle")
        .text(priced ? `Historical listed price (${options.currency})` : "Candidate position");
    svg.append("text")
        .attr("x", margin.left)
        .attr("y", 16)
        .text(
            options.scoreType === "probability"
                ? "Model probability"
                : "Decision score · not a probability"
        );
    if (Number.isFinite(options.threshold)) {
        svg.append("line")
            .attr("x1", margin.left)
            .attr("x2", width - margin.right)
            .attr("y1", y(options.threshold))
            .attr("y2", y(options.threshold))
            .attr("stroke", "#3457d5")
            .attr("stroke-dasharray", "6 4");
        svg.append("text")
            .attr("x", width - margin.right)
            .attr("y", y(options.threshold) - 7)
            .attr("text-anchor", "end")
            .text("Exploratory threshold");
    }
    const circles = svg
        .selectAll("circle")
        .data(points)
        .enter()
        .append("circle")
        .attr("cx", xValueWithScale)
        .attr("cy", (item) => y(item.prediction.raw_score))
        .attr("r", 7)
        .attr("fill", (item) => (options.isMatch(item) ? "#167454" : "#a73d39"))
        .attr("stroke", (item) => (item.product.id === options.selected ? "#192b42" : "white"))
        .attr("stroke-width", (item) => (item.product.id === options.selected ? 3 : 1.5))
        .attr("tabindex", 0)
        .attr("role", "button")
        .attr(
            "aria-label",
            (item) =>
                `${item.product.title}, score ${item.prediction.raw_score.toFixed(4)}. Select to compare.`
        )
        .on("click", options.select)
        .on("keydown", function (item) {
            if (d3.event.key === "Enter" || d3.event.key === " ") {
                d3.event.preventDefault();
                options.select(item);
            }
        });
    circles
        .append("title")
        .text(
            (item) =>
                `${item.product.title}\nVendor: ${item.product.seller || "Unknown"}\nPrice: ${item.product.price ?? "Unavailable"} ${item.product.currency || ""}\nScore: ${item.prediction.raw_score}`
        );
    function xValueWithScale(item, index) {
        return x(xValue(item, index));
    }
}

function drawPrecisionRecall(container, points) {
    if (!window.d3 || !points?.length) return;
    const svg = d3
        .select(container)
        .append("svg")
        .attr("viewBox", "0 0 600 260")
        .attr("role", "img")
        .attr("aria-label", "Precision recall curve from labeled evaluation");
    const x = d3.scaleLinear().domain([0, 1]).range([55, 570]);
    const y = d3.scaleLinear().domain([0, 1]).range([215, 25]);
    svg.append("g").attr("transform", "translate(0,215)").call(d3.axisBottom(x).ticks(5));
    svg.append("g").attr("transform", "translate(55,0)").call(d3.axisLeft(y).ticks(5));
    svg.append("text").attr("x", 280).attr("y", 250).text("Recall");
    svg.append("text").attr("x", 55).attr("y", 15).text("Precision");
    svg.append("path")
        .datum(points.slice().sort((a, b) => a.recall - b.recall))
        .attr("fill", "none")
        .attr("stroke", "#3457d5")
        .attr("stroke-width", 2)
        .attr(
            "d",
            d3
                .line()
                .x((p) => x(p.recall))
                .y((p) => y(p.precision))
        );
    svg.selectAll("circle")
        .data(points)
        .enter()
        .append("circle")
        .attr("cx", (p) => x(p.recall))
        .attr("cy", (p) => y(p.precision))
        .attr("r", 4)
        .attr("fill", "#3457d5")
        .append("title")
        .text((p) => `Threshold ${p.threshold}: precision ${p.precision}, recall ${p.recall}`);
}
