import os
import uuid
import traceback
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.pipeline.data_adapter import adapt_dataset
from app.pipeline.forecastings import recursive_forecast
from app.pipeline.inventory import calculate_inventory
from app.pipeline.segmentation import classify_demand
from app.services.session_store import create_session, get_session


# ============================================================
# BASE DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="DemandPulse AI",
    version="1.0.0",
    description="AI Demand Forecasting & Inventory Optimization Platform"
)


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


# ============================================================
# REQUEST MODELS
# ============================================================

class ForecastRequest(BaseModel):
    session_id: str
    product: str | None = None
    store: str | None = None
    horizon: int = 30
    current_stock: float = 0
    lead_time_days: int = 7
    safety_stock_days: int = 3


class CompareRequest(BaseModel):
    session_id: str
    product1: str
    product2: str
    store: str | None = None
    horizon: int = 30


# ============================================================
# HOME
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home():

    html_path = BASE_DIR / "templates" / "index.html"

    return html_path.read_text(
        encoding="utf-8"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "service": "DemandPulse AI"
    }


# ============================================================
# DATASET UPLOAD
# ============================================================

@app.post("/api/upload")
async def upload_dataset(
    file: UploadFile = File(...)
):

    # --------------------------------------------------------
    # Validate filename
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="Please select a CSV or Excel file."
        )


    # --------------------------------------------------------
    # Validate extension
    # --------------------------------------------------------

    extension = Path(
        file.filename
    ).suffix.lower()


    if extension not in [
        ".csv",
        ".xlsx",
        ".xls"
    ]:

        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Upload CSV, XLSX or XLS."
        )


    # --------------------------------------------------------
    # Create unique file
    # --------------------------------------------------------

    file_id = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    file_path = UPLOAD_DIR / file_id


    # --------------------------------------------------------
    # Save uploaded file
    # --------------------------------------------------------

    content = await file.read()

    file_path.write_bytes(content)


    # --------------------------------------------------------
    # Adapt dataset
    # --------------------------------------------------------

    try:

        data, metadata = adapt_dataset(
            file_path
        )

    except Exception as exc:

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=400,
            detail=f"Invalid Dataset: {str(exc)}"
        )


    # --------------------------------------------------------
    # Products
    # --------------------------------------------------------

    products = sorted(
        data["product"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


    # --------------------------------------------------------
    # Stores
    # --------------------------------------------------------

    stores = sorted(
        data["store"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


    # --------------------------------------------------------
    # Insights
    # --------------------------------------------------------

    insights = build_insights(
        data
    )


    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata = {

        "filename": file.filename,

        "rows": int(
            len(data)
        ),

        "products": int(
            data["product"].nunique()
        ),

        "stores": int(
            data["store"].nunique()
        ),

        "start_date": str(
            data["date"].min().date()
        ),

        "end_date": str(
            data["date"].max().date()
        )
    }


    # --------------------------------------------------------
    # Create session
    # --------------------------------------------------------

    session_id = create_session(
        data,
        metadata
    )


    # --------------------------------------------------------
    # Preview
    # --------------------------------------------------------

    preview = data.head(10).copy()

    preview["date"] = (
        preview["date"]
        .astype(str)
    )


    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {

        "success": True,

        "session_id": session_id,

        "metadata": metadata,

        "products": products,

        "stores": stores,

        "preview": preview.to_dict(
            orient="records"
        ),

        "insights": insights
    }


# ============================================================
# SELECT SERIES
# ============================================================

def select_series(
    data,
    product=None,
    store=None
):

    df = data.copy()


    # --------------------------------------------------------
    # Product filter
    # --------------------------------------------------------

    if product:

        df = df[
            df["product"]
            .astype(str)
            .str.strip()
            .str.casefold()
            == str(product).strip().casefold()
        ]


    # --------------------------------------------------------
    # Store filter
    # --------------------------------------------------------

    all_store_values = {
        "all",
        "all stores",
        "all_store",
        "all_stores",
        "total",
        "none",
        ""
    }

    if (
        store
        and str(store).strip().casefold()
        not in all_store_values
    ):

        df = df[
            df["store"]
            .astype(str)
            .str.strip()
            .str.casefold()
            == str(store).strip().casefold()
        ]


    # --------------------------------------------------------
    # Empty check
    # --------------------------------------------------------

    if df.empty:

        raise ValueError(
            "No demand history found "
            "for the selected product/store."
        )


    # --------------------------------------------------------
    # Group time series
    # --------------------------------------------------------

    group_cols = [
        "date"
    ]


    result = (

        df.groupby(
            group_cols,
            as_index=False
        )

        .agg({

            "quantity": "sum",

            "price": "mean",

            "discount": "mean"
        })

        .sort_values(
            "date"
        )
    )


    # --------------------------------------------------------
    # Add product/store
    # --------------------------------------------------------

    result["product"] = str(
        product or "ALL"
    )

    result["store"] = str(
        store or "ALL"
    )


    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return result[
        [
            "date",
            "quantity",
            "product",
            "store",
            "price",
            "discount"
        ]
    ]


# ============================================================
# FORECAST API
# ============================================================

@app.post("/api/forecast")
async def forecast(
    request: ForecastRequest
):

    try:

        # ====================================================
        # GET SESSION
        # ====================================================

        try:

            session = get_session(
                request.session_id
            )

        except KeyError:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Session expired. "
                    "Please upload the dataset again."
                )
            )


        data = session["data"].copy()


        # ====================================================
        # CLEAN PRODUCT
        # ====================================================

        data["product"] = (

            data["product"]

            .astype(str)

            .str.strip()
        )


        # ====================================================
        # CLEAN STORE
        # ====================================================

        data["store"] = (

            data["store"]

            .astype(str)

            .str.strip()
        )


        # ====================================================
        # PRODUCT
        # ====================================================

        product = request.product


        if not product:

            product = (
                data["product"]
                .iloc[0]
            )


        product = str(
            product
        ).strip()


        # ====================================================
        # PRODUCT FILTER
        # ====================================================

        product_mask = (

            data["product"]
            .str.casefold()

            == product.casefold()
        )


        filtered = data[
            product_mask
        ].copy()


        # ====================================================
        # STORE
        # ====================================================

        store = request.store


        if not store:

            store = "All Stores"


        store = str(
            store
        ).strip()


        # ====================================================
        # ALL STORE VALUES
        # ====================================================

        all_store_values = {

            "all",

            "all stores",

            "all_store",

            "all_stores",

            "total",

            "none",

            ""
        }


        # ====================================================
        # STORE FILTER
        # ====================================================

        if (
            store.casefold()
            not in all_store_values
        ):

            filtered = filtered[
                filtered["store"]
                .str.casefold()
                == store.casefold()
            ]


        # ====================================================
        # DEBUG
        # ====================================================

        print(
            "\n========== FORECAST DEBUG =========="
        )

        print(
            "Requested product:",
            product
        )

        print(
            "Requested store:",
            store
        )

        print(
            "Total dataset rows:",
            len(data)
        )

        print(
            "Product rows:",
            len(
                data[product_mask]
            )
        )

        print(
            "Filtered rows:",
            len(filtered)
        )

        print(
            "Available products:",
            data["product"]
            .unique()[:20]
            .tolist()
        )

        print(
            "Available stores:",
            data["store"]
            .unique()[:20]
            .tolist()
        )

        print(
            "====================================\n"
        )


        # ====================================================
        # NO DATA CHECK
        # ====================================================

        if filtered.empty:

            raise ValueError(
                "No demand history found "
                "for the selected product/store."
            )


        # ====================================================
        # CREATE TIME SERIES
        # ====================================================

        history = (
            filtered
            .groupby(
                ["date", "product", "store"],
                as_index=False
            )
            .agg({
                "quantity": "sum",
                "price": "mean",
                "discount": "mean"
            })
            .sort_values("date")
            .reset_index(drop=True)
        )


        # ====================================================
        # ALL STORES: ek date = ek row (stores ko sum karo)
        # ====================================================

        if history["date"].duplicated().any():

            history = (
                history
                .groupby(
                    "date",
                    as_index=False
                )
                .agg({
                    "quantity": "sum",
                    "price": "mean",
                    "discount": "mean",
                    "product": "first",
                    "store": "first"
                })
                .sort_values("date")
                .reset_index(drop=True)
            )

            history["store"] = store


        # ====================================================
        # HISTORY CHECK
        # ====================================================

        if history.empty:

            raise ValueError(
                "No demand history found "
                "after grouping the selected data."
            )


        if len(history) < 5:

            raise ValueError(
                "Not enough historical data. "
                f"Only {len(history)} "
                "time points found."
            )


        # ====================================================
        # FORECAST
        # ====================================================

        result = recursive_forecast(

            history,

            request.horizon
        )


        # ====================================================
        # VALIDATE FORECAST RESULT
        # ====================================================

        if not isinstance(
            result,
            dict
        ):

            raise ValueError(
                "Forecast model returned "
                "an invalid result."
            )


        if "forecast" not in result:

            raise KeyError(
                "Forecast result does not "
                "contain 'forecast'."
            )


        forecast_df = result[
            "forecast"
        ]


        if "forecast" not in forecast_df.columns:

            raise KeyError(
                "Forecast dataframe does not "
                "contain 'forecast' column."
            )


        # ====================================================
        # INVENTORY
        # ====================================================

        inventory = calculate_inventory(

            history[
                "quantity"
            ].values,

            forecast_df[
                "forecast"
            ].values,

            current_stock=(
                request.current_stock
            ),

            lead_time_days=(
                request.lead_time_days
            ),

            safety_stock_days=(
                request.safety_stock_days
            )
        )


        # ====================================================
        # FORECAST DATA
        # ====================================================

        forecast_rows = (
            forecast_df.copy()
        )


        forecast_rows["date"] = (

            forecast_rows["date"]

            .astype(str)
        )


        # ====================================================
        # HISTORY
        # ====================================================

        history_rows = (
            history
            .tail(120)
            .copy()
        )


        history_rows["date"] = (

            history_rows["date"]

            .astype(str)
        )


        # ====================================================
        # RESPONSE
        # ====================================================

        return {

            "success": True,

            "product": product,

            "store": store,

            "horizon": request.horizon,

            "model": result.get(
                "model"
            ),

            "segment": result.get(
                "segment"
            ),

            "frequency": result.get(
                "frequency"
            ),

            "rows_used": result.get(
                "rows_used"
            ),

            "metrics": result.get(
                "selected_metrics",
                {}
            ),

            "model_metrics": result.get(
                "model_metrics",
                {}
            ),

            "inventory": inventory,

            "forecast": (
                forecast_rows
                .to_dict(
                    orient="records"
                )
            ),

            "history": (

                history_rows[
                    [
                        "date",
                        "quantity"
                    ]
                ]

                .to_dict(
                    orient="records"
                )
            )
        }


    # ========================================================
    # HTTP ERROR
    # ========================================================

    except HTTPException:

        raise


    # ========================================================
    # REAL FORECAST ERROR
    # ========================================================

    except Exception as exc:

        print(
            "\n========== FORECAST ERROR =========="
        )

        print(
            "Exception type:",
            type(exc).__name__
        )

        print(
            "Exception:",
            str(exc)
        )

        traceback.print_exc()

        print(
            "====================================\n"
        )


        raise HTTPException(

            status_code=400,

            detail=(
                "Forecast failed: "
                f"{type(exc).__name__}: "
                f"{str(exc)}"
            )
        )


# ============================================================
# COMPARE PRODUCTS
# ============================================================

@app.post("/api/compare")
async def compare_products(
    request: CompareRequest
):

    try:

        # ----------------------------------------------------
        # GET SESSION
        # ----------------------------------------------------

        try:

            session = get_session(
                request.session_id
            )

        except KeyError:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Session expired. "
                    "Please upload the dataset again."
                )
            )


        data = session["data"]


        # ----------------------------------------------------
        # RESULTS
        # ----------------------------------------------------

        results = []


        # ----------------------------------------------------
        # PROCESS PRODUCTS
        # ----------------------------------------------------

        for product in [

            request.product1,

            request.product2

        ]:

            history = select_series(

                data,

                product,

                request.store or "ALL"
            )


            result = recursive_forecast(

                history,

                request.horizon
            )


            results.append({

                "product": product,

                "model": result.get(
                    "model"
                ),

                "segment": result.get(
                    "segment"
                ),

                "forecast": (

                    result["forecast"][

                        [
                            "date",
                            "forecast"
                        ]

                    ]

                    .assign(

                        date=lambda x:
                        x["date"].astype(str)

                    )

                    .to_dict(
                        orient="records"
                    )
                )
            })


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "success": True,

            "products": results
        }


    # ========================================================
    # HTTP ERROR
    # ========================================================

    except HTTPException:

        raise


    # ========================================================
    # COMPARE ERROR
    # ========================================================

    except Exception as exc:

        print(
            "\n========== COMPARE ERROR =========="
        )

        print(
            "Exception type:",
            type(exc).__name__
        )

        print(
            "Exception:",
            str(exc)
        )

        traceback.print_exc()

        print(
            "===================================\n"
        )


        raise HTTPException(

            status_code=400,

            detail=(
                "Compare failed: "
                f"{type(exc).__name__}: "
                f"{str(exc)}"
            )
        )


# ============================================================
# INSIGHTS
# ============================================================

@app.get("/api/insights/{session_id}")
async def insights(
    session_id: str
):

    try:

        session = get_session(
            session_id
        )


        return build_insights(

            session["data"]
        )


    except KeyError:

        raise HTTPException(

            status_code=404,

            detail="Session expired."
        )


# ============================================================
# BUILD INSIGHTS
# ============================================================

def build_insights(
    data
):

    # --------------------------------------------------------
    # PRODUCT TOTALS
    # --------------------------------------------------------

    product_totals = (

        data

        .groupby(
            "product"
        )["quantity"]

        .sum()

        .sort_values(
            ascending=False
        )
    )


    # --------------------------------------------------------
    # SEGMENTS
    # --------------------------------------------------------

    segments = {}


    # --------------------------------------------------------
    # EACH PRODUCT
    # --------------------------------------------------------

    for product in data[
        "product"
    ].unique():

        product_data = data[
            data["product"] == product
        ]


        # ----------------------------------------------------
        # TIME SERIES
        # ----------------------------------------------------

        series = (

            product_data

            .groupby(
                "date"
            )["quantity"]

            .sum()

            .sort_index()
        )


        # ----------------------------------------------------
        # CLASSIFY
        # ----------------------------------------------------

        segment = classify_demand(

            series.values
        )


        segments[segment] = (

            segments.get(
                segment,
                0
            )

            + 1
        )


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "total_demand": round(

            float(
                data["quantity"].sum()
            ),

            2
        ),

        "average_demand": round(

            float(
                data["quantity"].mean()
            ),

            2
        ),

        "max_demand": round(

            float(
                data["quantity"].max()
            ),

            2
        ),

        "top_products": [

            {

                "product": str(
                    index
                ),

                "demand": round(
                    float(value),
                    2
                )
            }

            for index, value
            in product_totals
            .head(10)
            .items()
        ],

        "segments": segments
    }