
let sessionId = null;
let selectedHorizon = 30;
let forecastChart = null;
let lastForecast = null;

const $ = (id) => document.getElementById(id);

// RESTORE SAVED SESSION
try {
    sessionId = sessionStorage.getItem("demandpulse_session_id");
} catch (error) {
    console.warn("Could not restore session:", error);
}

// ERROR / UI HELPERS
function showError(message) {
    const box = $("alertBox");

    if (!box) {
        console.error(message);
        return;
    }

    box.textContent = message;
    box.style.display = "block";
}

function hideError() {
    const box = $("alertBox");
    if (box) box.style.display = "none";
}

function setLoading(status) {
    const loadingText = $("loadingText");
    const forecastBtn = $("forecastBtn");

    if (loadingText) {
        loadingText.style.display = status ? "inline" : "none";
    }

    if (forecastBtn) {
        forecastBtn.disabled = status;
    }
}

function formatNumber(value) {
    if (
        value === null ||
        value === undefined ||
        value === "" ||
        !Number.isFinite(Number(value))
    ) {
        return "—";
    }

    return Number(value).toLocaleString("en-IN", {
        maximumFractionDigits: 2
    });
}

// API RESPONSE HANDLING
// Handles JSON responses and HTML proxy errors such as Render 502 pages.
async function readApiResponse(response) {
    const contentType = response.headers.get("content-type") || "";
    let result = {};

    if (contentType.includes("application/json")) {
        try {
            result = await response.json();
        } catch (_) {
            throw new Error(
                `Server returned invalid JSON (HTTP ${response.status}). Please retry.`
            );
        }
    } else {
        // Do not expose large HTML/CSS error pages to the user.
        if (!response.ok) {
            const messages = {
                502: "The server gateway is temporarily unavailable. Wait a moment and retry.",
                503: "The server is temporarily unavailable. Please retry shortly.",
                504: "The server took too long to respond. Try again with a shorter forecast horizon."
            };

            throw new Error(
                messages[response.status] ||
                `Server request failed (HTTP ${response.status}). Please retry.`
            );
        }

        throw new Error(
            "The server returned an unexpected response. Please refresh and retry."
        );
    }

    if (!response.ok) {
        const detail = String(
            result.detail || result.message || result.error || ""
        );

        if (
            response.status === 404 &&
            /session/i.test(detail)
        ) {
            sessionId = null;

            try {
                sessionStorage.removeItem("demandpulse_session_id");
            } catch (_) {}

            throw new Error(
                "Your upload session has expired. Please upload the dataset again."
            );
        }

        throw new Error(
            detail || `Request failed (HTTP ${response.status}).`
        );
    }

    return result;
}

// SAFE FETCH WITH OPTIONAL TIMEOUT
// Aborting a browser request does not guarantee the server stops processing it.
async function fetchWithTimeout(url, options = {}, timeoutMs = 90000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        return await fetch(url, {
            ...options,
            signal: controller.signal
        });
    } catch (error) {
        if (error.name === "AbortError") {
            throw new Error(
                "The request took too long. The server may still be processing it. Please retry."
            );
        }

        if (!navigator.onLine) {
            throw new Error(
                "You appear to be offline. Check your internet connection and retry."
            );
        }

        throw new Error(
            "Could not connect to the server. Check your connection or retry in a moment."
        );
    } finally {
        clearTimeout(timeoutId);
    }
}

// HORIZON
function setHorizon(days) {
    const parsedDays = Number(days);

    if (!Number.isFinite(parsedDays) || parsedDays <= 0) {
        return;
    }

    selectedHorizon = parsedDays;

    document.querySelectorAll(".horizon button").forEach(button => {
        button.classList.toggle(
            "active",
            Number(button.dataset.days) === selectedHorizon
        );
    });
}

// FILE UPLOAD
const fileInput = $("fileInput");

if (fileInput) {
    fileInput.addEventListener("change", async function () {
        const file = this.files && this.files[0];

        if (!file) return;

        const selectedFile = $("selectedFile");

        if (selectedFile) {
            selectedFile.textContent = `Selected: ${file.name}`;
            selectedFile.style.display = "block";
        }

        await uploadDataset(file);
    });
}

async function uploadDataset(file) {
    hideError();
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetchWithTimeout(
            "/api/upload",
            {
                method: "POST",
                body: formData
            },
            120000
        );

        const result = await readApiResponse(response);

        if (!result.session_id) {
            throw new Error(
                "Upload completed, but the server did not return a session ID."
            );
        }

        sessionId = result.session_id;

        try {
            sessionStorage.setItem(
                "demandpulse_session_id",
                sessionId
            );
        } catch (error) {
            console.warn("Could not save session ID:", error);
        }

        populateProductSelect(
            $("productSelect"),
            result.products || []
        );

        populateStoreSelect(
            $("storeSelect"),
            result.stores || []
        );

        populateProductSelect(
            $("compareProduct1"),
            result.products || []
        );

        populateProductSelect(
            $("compareProduct2"),
            result.products || []
        );

        renderDatasetInfo(result.metadata || {});
        renderInsights(result.insights || {});

        const workspace = $("workspace");

        if (workspace) {
            workspace.style.display = "block";

            window.scrollTo({
                top: workspace.offsetTop - 20,
                behavior: "smooth"
            });
        }

        // A new dataset invalidates the previous forecast.
        lastForecast = null;

        const downloadBtn = $("downloadBtn");
        if (downloadBtn) downloadBtn.disabled = true;

        const compareTable = $("compareTable");
        if (compareTable) compareTable.innerHTML = "";

    } catch (error) {
        console.error("UPLOAD ERROR:", error);
        showError(error.message || "Dataset upload failed.");
    } finally {
        setLoading(false);
    }
}

// PRODUCT DROPDOWN
function populateProductSelect(select, values) {
    if (!select) return;

    select.innerHTML = "";

    if (!Array.isArray(values) || values.length === 0) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "No products available";
        select.appendChild(option);
        return;
    }

    values.forEach(value => {
        const option = document.createElement("option");
        option.value = String(value);
        option.textContent = String(value);
        select.appendChild(option);
    });
}

// STORE DROPDOWN
function populateStoreSelect(select, values) {
    if (!select) return;

    select.innerHTML = "";

    const allOption = document.createElement("option");
    allOption.value = "All Stores";
    allOption.textContent = "All Stores";
    select.appendChild(allOption);

    if (!Array.isArray(values)) return;

    values.forEach(value => {
        const cleanValue = String(value).trim();

        if (
            !cleanValue ||
            cleanValue.toLowerCase() === "all stores" ||
            cleanValue.toLowerCase() === "all"
        ) {
            return;
        }

        const option = document.createElement("option");
        option.value = cleanValue;
        option.textContent = cleanValue;
        select.appendChild(option);
    });
}

// FORECAST
async function runForecast() {
    if (!sessionId) {
        showError("Please upload a dataset first.");
        return;
    }

    hideError();
    setLoading(true);

    try {
        const product = $("productSelect")?.value;
        const store = $("storeSelect")?.value || "All Stores";

        if (!product) {
            throw new Error("Please select a product.");
        }

        const payload = {
            session_id: sessionId,
            product,
            store,
            horizon: Number(selectedHorizon || 30),
            current_stock: Number($("stockInput")?.value || 0),
            lead_time_days: Number($("leadTimeInput")?.value || 7),
            safety_stock_days: Number($("safetyInput")?.value || 3)
        };

        console.log("FORECAST REQUEST:", payload);

        const response = await fetchWithTimeout(
            "/api/forecast",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            },
            120000
        );

        const result = await readApiResponse(response);

        console.log("FORECAST RESPONSE:", result);

        lastForecast = result;

        renderForecast(result);
        renderModelMetrics(result.model_metrics || {});
        renderInventory(result.inventory || {});

        const downloadBtn = $("downloadBtn");
        if (downloadBtn) downloadBtn.disabled = false;

    } catch (error) {
        console.error("FORECAST ERROR:", error);
        showError(error.message || "Forecast failed.");
    } finally {
        setLoading(false);
    }
}

// RENDER FORECAST
function renderForecast(result) {
    const modelValue = $("modelValue");
    const segmentValue = $("segmentValue");
    const wapeValue = $("wapeValue");
    const avgDemandValue = $("avgDemandValue");
    const forecastDemandValue = $("forecastDemandValue");
    const chartSubtitle = $("chartSubtitle");

    if (modelValue) modelValue.textContent = result.model || "—";

    if (segmentValue) {
        segmentValue.textContent = result.segment
            ? `${result.segment} demand`
            : "—";
    }

    if (wapeValue) {
        wapeValue.textContent =
            result.metrics?.WAPE !== undefined
                ? `${formatNumber(result.metrics.WAPE)}%`
                : "—";
    }

    const forecast = result.forecast || [];
    const history = result.history || [];

    const forecastTotal = forecast.reduce(
        (sum, item) => sum + Number(item.forecast || 0),
        0
    );

    const historyAverage = history.length
        ? history.reduce(
            (sum, item) => sum + Number(item.quantity || 0),
            0
        ) / history.length
        : 0;

    if (avgDemandValue) {
        avgDemandValue.textContent = formatNumber(historyAverage);
    }

    if (forecastDemandValue) {
        forecastDemandValue.textContent = formatNumber(forecastTotal);
    }

    if (chartSubtitle) {
        chartSubtitle.textContent =
            `${result.product || "Product"} • ` +
            `${result.horizon || selectedHorizon}-period forecast`;
    }

    drawForecastChart(result);
}

// FORECAST CHART
function drawForecastChart(result) {
    const canvas = $("forecastChart");

    if (!canvas || typeof Chart === "undefined") {
        console.warn("Forecast chart canvas or Chart.js is unavailable.");
        return;
    }

    if (forecastChart) {
        forecastChart.destroy();
        forecastChart = null;
    }

    const history = result.history || [];
    const forecast = result.forecast || [];

    const labels = [
        ...history.map(item => item.date),
        ...forecast.map(item => item.date)
    ];

    const historicalValues = [
        ...history.map(item => Number(item.quantity || 0)),
        ...forecast.map(() => null)
    ];

    const forecastValues = [
        ...history.map(() => null),
        ...forecast.map(item => Number(item.forecast || 0))
    ];

    const lowerValues = [
        ...history.map(() => null),
        ...forecast.map(item => Number(item.lower ?? 0))
    ];

    const upperValues = [
        ...history.map(() => null),
        ...forecast.map(item => Number(item.upper ?? 0))
    ];

    forecastChart = new Chart(canvas, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Historical Demand",
                    data: historicalValues,
                    borderWidth: 2,
                    tension: 0.35,
                    pointRadius: 0
                },
                {
                    label: "Forecast",
                    data: forecastValues,
                    borderWidth: 3,
                    tension: 0.35,
                    pointRadius: 2
                },
                {
                    label: "80% Upper",
                    data: upperValues,
                    borderWidth: 1,
                    borderDash: [5, 5],
                    pointRadius: 0
                },
                {
                    label: "80% Lower",
                    data: lowerValues,
                    borderWidth: 1,
                    borderDash: [5, 5],
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false
            },
            plugins: {
                legend: {
                    labels: {
                        color: "#91a0b5"
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: "#718198",
                        maxTicksLimit: 10
                    },
                    grid: {
                        color: "rgba(255,255,255,.04)"
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: "#718198"
                    },
                    grid: {
                        color: "rgba(255,255,255,.04)"
                    }
                }
            }
        }
    });
}

// MODEL METRICS
function renderModelMetrics(metrics) {
    const container = $("modelList");
    if (!container) return;

    container.innerHTML = "";

    Object.entries(metrics || {}).forEach(([name, metric]) => {
        const row = document.createElement("div");
        row.className = "model-row";

        if (lastForecast && name === lastForecast.model) {
            row.classList.add("best");
        }

        const nameBlock = document.createElement("div");
        const modelName = document.createElement("strong");
        modelName.textContent = name;
        nameBlock.appendChild(modelName);

        if (lastForecast && name === lastForecast.model) {
            const selected = document.createElement("span");
            selected.textContent = " • Selected";
            nameBlock.appendChild(selected);
        }

        const metricBlock = document.createElement("div");
        const score = document.createElement("strong");
        score.textContent = `${formatNumber(metric?.WAPE)}%`;

        const label = document.createElement("span");
        label.textContent = " WAPE";

        metricBlock.appendChild(score);
        metricBlock.appendChild(label);

        row.appendChild(nameBlock);
        row.appendChild(metricBlock);
        container.appendChild(row);
    });
}

// INVENTORY
function renderInventory(inventory) {
    const status = $("inventoryStatus");
    const grid = $("inventoryGrid");

    if (status) {
        const risk = String(inventory.risk || "Low")
            .toLowerCase()
            .replace(/[^a-z0-9_-]/g, "");

        status.innerHTML = "";

        const badge = document.createElement("span");
        badge.className = `risk risk-${risk}`;
        badge.textContent = inventory.status || "—";
        status.appendChild(badge);
    }

    if (!grid) return;

    const values = [
        ["Current Stock", inventory.current_stock],
        ["Reorder Point", inventory.reorder_point],
        ["Safety Stock", inventory.safety_stock],
        ["Reorder Quantity", inventory.reorder_quantity],
        ["Lead-Time Demand", inventory.lead_time_demand],
        ["Stock After Forecast", inventory.stock_after_forecast]
    ];

    grid.innerHTML = "";

    values.forEach(([label, value]) => {
        const item = document.createElement("div");
        item.className = "inventory-item";

        const small = document.createElement("small");
        small.textContent = label;

        const strong = document.createElement("strong");
        strong.textContent = formatNumber(value);

        item.appendChild(small);
        item.appendChild(strong);
        grid.appendChild(item);
    });
}

// INSIGHTS
function renderInsights(insights) {
    const container = $("insightList");
    if (!container) return;

    const topProduct = insights.top_products?.[0];

    const values = [
        ["Total Demand", formatNumber(insights.total_demand)],
        ["Average Demand", formatNumber(insights.average_demand)],
        ["Maximum Demand", formatNumber(insights.max_demand)],
        ["Top Product", topProduct?.product || "—"],
        ["Top Product Demand", topProduct
            ? formatNumber(topProduct.demand)
            : "—"]
    ];

    container.innerHTML = "";

    values.forEach(([label, value]) => {
        const item = document.createElement("div");
        item.className = "insight";

        const name = document.createElement("span");
        name.textContent = label;

        const result = document.createElement("strong");
        result.textContent = value;

        item.appendChild(name);
        item.appendChild(result);
        container.appendChild(item);
    });
}

// DATASET INFO
function renderDatasetInfo(metadata) {
    const container = $("datasetInfo");
    if (!container) return;

    const values = [
        ["File", metadata.filename || "—"],
        ["Rows", formatNumber(metadata.rows)],
        ["Products", formatNumber(metadata.products)],
        ["Stores", formatNumber(metadata.stores)],
        ["Start", metadata.start_date || "—"],
        ["End", metadata.end_date || "—"]
    ];

    container.innerHTML = "";

    values.forEach(([label, value]) => {
        const item = document.createElement("div");
        item.className = "insight";

        const name = document.createElement("span");
        name.textContent = label;

        const result = document.createElement("strong");
        result.textContent = value;

        item.appendChild(name);
        item.appendChild(result);
        container.appendChild(item);
    });
}

// COMPARE PRODUCTS
async function compareProducts() {
    if (!sessionId) {
        showError("Please upload a dataset first.");
        return;
    }

    const product1 = $("compareProduct1")?.value;
    const product2 = $("compareProduct2")?.value;

    if (!product1 || !product2) {
        showError("Select two products to compare.");
        return;
    }

    hideError();

    const compareButton = $("compareBtn");
    if (compareButton) compareButton.disabled = true;

    try {
        const response = await fetchWithTimeout(
            "/api/compare",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    product1,
                    product2,
                    store: $("storeSelect")?.value || "All Stores",
                    horizon: selectedHorizon
                })
            },
            120000
        );

        const result = await readApiResponse(response);
        const products = result.products || [];
        const table = $("compareTable");

        if (!table) {
            throw new Error("Comparison table was not found on the page.");
        }

        table.innerHTML = "";

        if (!products.length) {
            table.textContent = "No comparison results returned.";
            return;
        }

        products.forEach(item => {
            const total = (item.forecast || []).reduce(
                (sum, row) => sum + Number(row.forecast || 0),
                0
            );

            const tr = document.createElement("tr");

            [
                item.product ?? "—",
                item.model ?? "—",
                item.segment ?? "—",
                formatNumber(total)
            ].forEach(value => {
                const td = document.createElement("td");
                td.textContent = String(value);
                tr.appendChild(td);
            });

            table.appendChild(tr);
        });

    } catch (error) {
        console.error("COMPARE ERROR:", error);
        showError(error.message || "Comparison failed.");
    } finally {
        if (compareButton) compareButton.disabled = false;
    }
}

// DOWNLOAD FORECAST
function downloadForecast() {
    if (!lastForecast) {
        showError("Run a forecast before downloading.");
        return;
    }

    const rows = [
        ["Date", "Forecast", "Lower_80", "Upper_80"]
    ];

    (lastForecast.forecast || []).forEach(item => {
        rows.push([
            item.date ?? "",
            item.forecast ?? "",
            item.lower ?? "",
            item.upper ?? ""
        ]);
    });

    const csv = rows.map(row =>
        row.map(value =>
            `"${String(value).replace(/"/g, '""')}"`
        ).join(",")
    ).join("\n");

    const blob = new Blob(
        ["\uFEFF", csv],
        { type: "text/csv;charset=utf-8;" }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download =
        `DemandPulse_${lastForecast.product || "Forecast"}_${lastForecast.horizon || selectedHorizon}D.csv`;

    document.body.appendChild(link);
    link.click();
    link.remove();

    // Delay revocation slightly for browser compatibility.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// RESET
function resetApp() {
    sessionId = null;
    lastForecast = null;

    try {
        sessionStorage.removeItem("demandpulse_session_id");
    } catch (error) {
        console.warn("Could not clear saved session:", error);
    }

    if (forecastChart) {
        forecastChart.destroy();
        forecastChart = null;
    }

    const workspace = $("workspace");
    if (workspace) workspace.style.display = "none";

    const fileInput = $("fileInput");
    if (fileInput) fileInput.value = "";

    const selectedFile = $("selectedFile");
    if (selectedFile) {
        selectedFile.textContent = "";
        selectedFile.style.display = "none";
    }

    const downloadBtn = $("downloadBtn");
    if (downloadBtn) downloadBtn.disabled = true;

    [
        "modelValue",
        "segmentValue",
        "wapeValue",
        "avgDemandValue",
        "forecastDemandValue"
    ].forEach(id => {
        const element = $(id);
        if (element) element.textContent = "—";
    });

    const modelList = $("modelList");
    if (modelList) modelList.innerHTML = "";

    const inventoryStatus = $("inventoryStatus");
    if (inventoryStatus) inventoryStatus.innerHTML = "";

    const inventoryGrid = $("inventoryGrid");
    if (inventoryGrid) inventoryGrid.innerHTML = "";

    const insightList = $("insightList");
    if (insightList) insightList.innerHTML = "";

    const datasetInfo = $("datasetInfo");
    if (datasetInfo) datasetInfo.innerHTML = "";

    const compareTable = $("compareTable");
    if (compareTable) compareTable.innerHTML = "";

    hideError();

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}

// INITIALIZE
setHorizon(30);
