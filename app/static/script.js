let sessionId = null;
let selectedHorizon = 30;
let forecastChart = null;
let lastForecast = null;

const $ = (id) => document.getElementById(id);


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

    if (!box) return;

    box.style.display = "none";
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
        Number.isNaN(Number(value))
    ) {
        return "—";
    }

    return Number(value).toLocaleString("en-IN", {
        maximumFractionDigits: 2
    });
}

// HORIZON
function setHorizon(days) {
    selectedHorizon = Number(days);
    document.querySelectorAll(".horizon button").forEach(button => {
        button.classList.toggle(
            "active",
            Number(button.dataset.days) === selectedHorizon
        );
    });
}

// Read API responses safely. Render/proxy failures can return HTML instead of JSON.
async function readApiResponse(response) {
    const contentType = response.headers.get("content-type") || "";
    const body = await response.text();
    let result;

    if (contentType.includes("application/json")) {
        try {
            result = body ? JSON.parse(body) : {};
        } catch (_) {
            throw new Error(`Server returned invalid JSON (HTTP ${response.status}). Please retry.`);
        }
    } else {
        const shortBody = body.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 180);
        if (!response.ok) {
            throw new Error(`Server error (HTTP ${response.status}). ${shortBody || "Please retry in a minute."}`);
        }
        throw new Error(`Server returned an unexpected response (HTTP ${response.status}). Please retry.`);
    }

    if (!response.ok) {
        throw new Error(result.detail || result.message || `Request failed (HTTP ${response.status}).`);
    }
    return result;
}

// FILE UPLOAD
$("fileInput").addEventListener("change", async function () {
    const file = this.files[0];

    if (!file) {
        return;
    }
    $("selectedFile").textContent =
        `Selected: ${file.name}`;
    $("selectedFile").style.display = "block";
    await uploadDataset(file);
});


async function uploadDataset(file) {

    hideError();
    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {

        const response = await fetch(
            "/api/upload",
            {
                method: "POST",
                body: formData
            }
        );

        const result = await readApiResponse(response);

        // SAVE SESSION ID
        if (!result.session_id) {
            throw new Error(
                "Upload succeeded but server did not return a session ID."
            );
        }

        sessionId = result.session_id;
        // Save temporarily in browser too
        sessionStorage.setItem(
            "demandpulse_session_id",
            sessionId
        );


        // PRODUCT DROPDOWN
        // IMPORTANT:
        // NO "ALL STORES" HERE
        populateProductSelect(
            $("productSelect"),
            result.products || []
        );

        // STORE DROPDOWN
        // "ALL STORES" ONLY HERE

        populateStoreSelect(
            $("storeSelect"),
            result.stores || []
        );

        // COMPARISON PRODUCTS
        populateProductSelect(
            $("compareProduct1"),
            result.products || []
        );

        populateProductSelect(
            $("compareProduct2"),
            result.products || []
        );

        // DATASET INFORMATION
        renderDatasetInfo(
            result.metadata || {}
        );

        renderInsights(
            result.insights || {}
        );

        // SHOW WORKSPACE
        $("workspace").style.display = "block";
        window.scrollTo({
            top: $("workspace").offsetTop - 20,
            behavior: "smooth"
        });


    } catch (error) {
        console.error(
            "UPLOAD ERROR:",
            error
        );

        showError(
            error.message ||
            "Dataset upload failed."
        );

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
        option.textContent =
            "No products available";
        select.appendChild(option);
        return;
    }


    values.forEach(value => {
        const option =
            document.createElement("option");
        option.value = String(value);
        option.textContent = String(value);
        select.appendChild(option);
    });
}

// STORE DROPDOWN
function populateStoreSelect(select, values) {
    if (!select) return;
    select.innerHTML = "";

    // IMPORTANT:
    // All Stores belongs ONLY to store dropdown

    const allOption =
        document.createElement("option");
    allOption.value = "All Stores";
    allOption.textContent = "All Stores";
    select.appendChild(allOption);

    if (!Array.isArray(values)) {
        return;
    }

    values.forEach(value => {
        const cleanValue =
            String(value).trim();

        // Don't duplicate All Stores
        if (
            cleanValue.toLowerCase() ===
            "all stores".toLowerCase()
        ) {
            return;
        }

        if (
            cleanValue.toLowerCase() ===
            "all"
        ) {
            return;
        }


        const option =
            document.createElement("option");
        option.value = cleanValue;
        option.textContent = cleanValue;
        select.appendChild(option);
    });
}

// FORECAST
async function runForecast() {
    if (!sessionId) {
        showError(
            "Please upload a dataset first."
        );

        return;
    }

    hideError();
    setLoading(true);

    try {

        // GET FORM VALUES
        const product =
            $("productSelect").value;

        const store =
            $("storeSelect").value || "All Stores";

        if (!product) {
            throw new Error(
                "Please select a product."
            );
        }

        // BUILD REQUEST
        const payload = {
            session_id: sessionId,
            product: product,
            store: store,
            horizon: Number(
                selectedHorizon || 30
            ),

            current_stock: Number(
                $("stockInput").value || 0
            ),

            lead_time_days: Number(
                $("leadTimeInput").value || 7
            ),

            safety_stock_days: Number(
                $("safetyInput").value || 3
            )
        };


        console.log(
            "FORECAST REQUEST:",
            payload
        );


        // API REQUEST
        const response =
            await fetch(
                "/api/forecast",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body:
                        JSON.stringify(payload)
                }
            );


        const result = await readApiResponse(response);

        console.log(
            "FORECAST RESPONSE:",
            result
        );

        // SESSION ERROR
        if (
            response.status === 404 &&
            String(result.detail || "")
                .toLowerCase()
                .includes("session")
        ) {

            sessionId = null;
            sessionStorage.removeItem(
                "demandpulse_session_id"
            );

            throw new Error(
                "Your upload session has expired. Please upload the dataset again."
            );
        }

        // OTHER API ERROR
        if (!response.ok) {
            throw new Error(
                result.detail ||
                result.error ||
                "Forecast failed."
            );
        }


        // SAVE RESULT
        lastForecast = result;


        // RENDER DASHBOARD
        renderForecast(result);
        renderModelMetrics(
            result.model_metrics || {}
        );

        renderInventory(
            result.inventory || {}
        );

        // DOWNLOAD
        $("downloadBtn").disabled = false;

    } catch (error) {
        console.error(
            "FORECAST ERROR:",
            error
        );

        showError(
            error.message ||
            "Forecast failed."
        );

    } finally {
        setLoading(false);
    }
}

// RENDER FORECAST
function renderForecast(result) {
    $("modelValue").textContent =
        result.model || "—";

    $("segmentValue").textContent =
        result.segment
            ? `${result.segment} demand`
            : "—";

    $("wapeValue").textContent =
        result.metrics &&
        result.metrics.WAPE !== undefined
            ? `${formatNumber(result.metrics.WAPE)}%`
            : "—";

    const forecast =
        result.forecast || [];

    const history =
        result.history || [];

    const forecastTotal =
        forecast.reduce(
            (sum, item) =>
                sum +
                Number(
                    item.forecast || 0
                ),
            0
        );


    const historyTotal =
        history.length
            ? history.reduce(
                (sum, item) =>
                    sum +
                    Number(
                        item.quantity || 0
                    ),
                0
            ) / history.length
            : 0;

    $("avgDemandValue").textContent =
        formatNumber(historyTotal);

    $("forecastDemandValue").textContent =
        formatNumber(forecastTotal);

    $("chartSubtitle").textContent =
        `${result.product || "Product"} • ` +
        `${result.horizon || selectedHorizon}-period forecast`;

    drawForecastChart(result);
}


// FORECAST CHART
function drawForecastChart(result) {
    const canvas =
        $("forecastChart");

    if (!canvas) return;
    if (forecastChart) {
        forecastChart.destroy();
        forecastChart = null;
    }


    const history =
        result.history || [];

    const forecast =
        result.forecast || [];

    const labels = [
        ...history.map(
            item => item.date
        ),

        ...forecast.map(
            item => item.date
        )
    ];


    const historicalValues = [
        ...history.map(
            item =>
                Number(
                    item.quantity || 0
                )
        ),

        ...forecast.map(
            () => null
        )
    ];

    const forecastValues = [
        ...history.map(
            () => null
        ),

        ...forecast.map(
            item =>
                Number(
                    item.forecast || 0
                )
        )
    ];


    const lowerValues = [
        ...history.map(
            () => null
        ),
        ...forecast.map(
            item =>
                Number(
                    item.lower || 0
                )
        )
    ];


    const upperValues = [
        ...history.map(
            () => null
        ),

        ...forecast.map(
            item =>
                Number(
                    item.upper || 0
                )
        )
    ];


    forecastChart =
        new Chart(
            canvas,
            {

                type: "line",
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label:
                                "Historical Demand",
                            data:
                                historicalValues,
                            borderWidth: 2,
                            tension: 0.35,
                            pointRadius: 0
                        },


                        {
                            label:
                                "Forecast",
                            data:
                                forecastValues,
                            borderWidth: 3,
                            tension: 0.35,
                            pointRadius: 2
                        },


                        {
                            label:
                                "80% Upper",
                            data:
                                upperValues,
                            borderWidth: 1,
                            borderDash: [5, 5],
                            pointRadius: 0
                        },


                        {
                            label:
                                "80% Lower",
                            data:
                                lowerValues,
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
                                color:
                                    "#91a0b5"
                            }
                        }
                    },


                    scales: {
                        x: {
                            ticks: {
                                color:
                                    "#718198",
                                maxTicksLimit: 10
                            },

                            grid: {
                                color:
                                    "rgba(255,255,255,.04)"
                            }
                        },

                        y: {

                            beginAtZero: true,
                            ticks: {
                                color:
                                    "#718198"
                            },

                            grid: {
                                color:
                                    "rgba(255,255,255,.04)"
                            }
                        }

                    }
                }
            }
        );
}


// MODEL METRICS
function renderModelMetrics(metrics) {
    const container =
        $("modelList");


    if (!container) return;
    container.innerHTML = "";

    Object.entries(
        metrics || {}
    ).forEach(
        ([name, metric]) => {
            const row =
                document.createElement("div");

            row.className =
                "model-row";

            if (
                lastForecast &&
                name === lastForecast.model
            ) {

                row.classList.add("best");
            }

            row.innerHTML = `
                <div>
                    <strong>
                        ${name}
                    </strong>

                    ${
                        name === lastForecast?.model
                            ? "<span> • Selected</span>"
                            : ""
                    }
                </div>

                <div>
                    <strong>
                        ${
                            formatNumber(
                                metric.WAPE
                            )
                        }%
                    </strong>

                    <span>
                        WAPE
                    </span>

                </div>
            `;
            container.appendChild(row);
        }
    );
}


// INVENTORY
function renderInventory(inventory) {
    const status =
        $("inventoryStatus");

    if (!status) return;

    const risk =
        String(
            inventory.risk || "Low"
        ).toLowerCase();

    status.innerHTML = `
        <span class="risk risk-${risk}">
            ${inventory.status || "—"}
        </span>

    `;


    const values = [

        [
            "Current Stock",
            inventory.current_stock
        ],

        [
            "Reorder Point",
            inventory.reorder_point
        ],

        [
            "Safety Stock",
            inventory.safety_stock
        ],

        [
            "Reorder Quantity",
            inventory.reorder_quantity
        ],

        [
            "Lead-Time Demand",
            inventory.lead_time_demand
        ],

        [
            "Stock After Forecast",
            inventory.stock_after_forecast
        ]
    ];


    $("inventoryGrid").innerHTML =

        values
            .map(
                item => `

                    <div class="inventory-item">

                        <small>
                            ${item[0]}
                        </small>

                        <strong>
                            ${formatNumber(item[1])}
                        </strong>

                    </div>

                `
            )
            .join("");
}

// INSIGHTS
function renderInsights(insights) {
    const topProduct =
        insights.top_products?.[0];

    $("insightList").innerHTML = `
        <div class="insight">
            <span>
                Total Demand
            </span>

            <strong>
                ${
                    formatNumber(
                        insights.total_demand
                    )
                }
            </strong>

        </div>


        <div class="insight">

            <span>
                Average Demand
            </span>

            <strong>
                ${
                    formatNumber(
                        insights.average_demand
                    )
                }
            </strong>

        </div>


        <div class="insight">

            <span>
                Maximum Demand
            </span>

            <strong>
                ${
                    formatNumber(
                        insights.max_demand
                    )
                }
            </strong>

        </div>


        <div class="insight">

            <span>
                Top Product
            </span>

            <strong>
                ${
                    topProduct
                        ? topProduct.product
                        : "—"
                }
            </strong>

        </div>


        <div class="insight">

            <span>
                Top Product Demand
            </span>

            <strong>
                ${
                    topProduct
                        ? formatNumber(
                            topProduct.demand
                        )
                        : "—"
                }
            </strong>

        </div>

    `;
}


// DATASET INFO
function renderDatasetInfo(metadata) {
    $("datasetInfo").innerHTML = `

        <div class="insight">

            <span>
                File
            </span>

            <strong>
                ${
                    metadata.filename || "—"
                }
            </strong>

        </div>


        <div class="insight">

            <span>
                Rows
            </span>

            <strong>
                ${
                    formatNumber(
                        metadata.rows
                    )
                }
            </strong>

        </div>


        <div class="insight">

            <span>
                Products
            </span>

            <strong>
                ${
                    formatNumber(
                        metadata.products
                    )
                }
            </strong>

        </div>


        <div class="insight">

            <span>
                Stores
            </span>

            <strong>
                ${
                    formatNumber(
                        metadata.stores
                    )
                }
            </strong>

        </div>


        <div class="insight">

            <span>
                Start
            </span>

            <strong>
                ${
                    metadata.start_date || "—"
                }
            </strong>

        </div>


        <div class="insight">

            <span>
                End
            </span>

            <strong>
                ${
                    metadata.end_date || "—"
                }
            </strong>

        </div>

    `;
}


// COMPARE PRODUCTS
async function compareProducts() {
    if (!sessionId) {

        showError(
            "Please upload a dataset first."
        );

        return;
    }


    const product1 =
        $("compareProduct1").value;


    const product2 =
        $("compareProduct2").value;


    if (!product1 || !product2) {

        showError(
            "Select two products to compare."
        );

        return;
    }


    try {

        hideError();


        const response =
            await fetch(
                "/api/compare",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            session_id:
                                sessionId,

                            product1:
                                product1,

                            product2:
                                product2,

                            store:
                                $("storeSelect").value,

                            horizon:
                                selectedHorizon
                        })
                }
            );


        const result = await readApiResponse(response);


        if (!response.ok) {

            throw new Error(
                result.detail ||
                "Comparison failed."
            );
        }


        const rows =
            (result.products || [])
                .map(item => {

                    const total =
                        (item.forecast || [])
                            .reduce(
                                (
                                    sum,
                                    row
                                ) =>
                                    sum +
                                    Number(
                                        row.forecast ||
                                        0
                                    ),
                                0
                            );


                    return `

                        <tr>

                            <td>
                                ${item.product}
                            </td>

                            <td>
                                ${item.model}
                            </td>

                            <td>
                                ${item.segment}
                            </td>

                            <td>
                                ${formatNumber(total)}
                            </td>

                        </tr>

                    `;
                })
                .join("");


        $("compareTable").innerHTML =
            rows;


    } catch (error) {

        console.error(
            "COMPARE ERROR:",
            error
        );

        showError(
            error.message ||
            "Comparison failed."
        );
    }
}


// DOWNLOAD FORECAST
function downloadForecast() {

    if (!lastForecast) {

        showError(
            "Run a forecast before downloading."
        );

        return;
    }


    const rows = [

        [
            "Date",
            "Forecast",
            "Lower_80",
            "Upper_80"
        ]

    ];


    (
        lastForecast.forecast || []
    ).forEach(item => {

        rows.push([

            item.date,

            item.forecast,

            item.lower,

            item.upper

        ]);
    });


    const csv =
        rows
            .map(
                row =>
                    row
                        .map(
                            value =>
                                `"${String(value)
                                    .replace(
                                        /"/g,
                                        '""'
                                    )}"`
                        )
                        .join(",")
            )
            .join("\n");


    const blob =
        new Blob(
            [csv],
            {
                type:
                    "text/csv;charset=utf-8;"
            }
        );


    const url =
        URL.createObjectURL(blob);


    const link =
        document.createElement("a");


    link.href = url;


    link.download =
        `DemandPulse_${lastForecast.product}_${selectedHorizon}D.csv`;


    document.body.appendChild(link);


    link.click();


    link.remove();


    URL.revokeObjectURL(url);
}


// RESET
function resetApp() {

    sessionId = null;

    lastForecast = null;


    // Clear browser session
    sessionStorage.removeItem(
        "demandpulse_session_id"
    );


    if (forecastChart) {

        forecastChart.destroy();

        forecastChart = null;
    }


    $("workspace").style.display =
        "none";


    $("fileInput").value = "";


    $("selectedFile").textContent =
        "";


    $("downloadBtn").disabled =
        true;


    $("modelValue").textContent =
        "—";


    $("wapeValue").textContent =
        "—";


    $("avgDemandValue").textContent =
        "—";


    $("forecastDemandValue").textContent =
        "—";


    hideError();


    window.scrollTo({

        top: 0,

        behavior: "smooth"
    });
}

// INITIALIZE
setHorizon(30);