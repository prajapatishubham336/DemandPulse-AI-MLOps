import logging
import uuid
import traceback
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.pipeline.data_adapter import adapt_dataset
from app.pipeline.forecasting import recursive_forecast
from app.pipeline.inventory import calculate_inventory
from app.pipeline.segmentation import classify_demand
from app.services.session_store import create_session, get_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demandpulse")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
ALLOWED_HORIZONS = {7, 30, 60, 90}

app = FastAPI(
    title="DemandPulse AI",
    version="1.1.0",
    description="AI Demand Forecasting & Inventory Optimization Platform",
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class ForecastRequest(BaseModel):
    session_id: str
    product: str | None = None
    store: str | None = None
    horizon: int = 30
    current_stock: float = Field(default=0, ge=0)
    lead_time_days: int = Field(default=7, ge=0, le=365)
    safety_stock_days: int = Field(default=3, ge=0, le=365)


class CompareRequest(BaseModel):
    session_id: str
    product1: str
    product2: str
    store: str | None = None
    horizon: int = 30


@app.get("/", response_class=HTMLResponse)
async def home():
    html_path = BASE_DIR / "templates" / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=500, detail="Dashboard template is missing.")
    return html_path.read_text(encoding="utf-8")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "DemandPulse AI"}


def _validate_horizon(horizon: int):
    if horizon not in ALLOWED_HORIZONS:
        raise HTTPException(
            status_code=422,
            detail=f"horizon must be one of {sorted(ALLOWED_HORIZONS)}",
        )


def _normalise_all_store(store):
    all_values = {"", "all", "all stores", "all_store", "all_stores", "total", "none"}
    if store is None or str(store).strip().casefold() in all_values:
        return None
    return str(store).strip()


def select_series(data, product=None, store=None):
    df = data.copy()
    if product:
        df = df[df["product"].astype(str).str.strip().str.casefold()
                == str(product).strip().casefold()]

    selected_store = _normalise_all_store(store)
    if selected_store:
        df = df[df["store"].astype(str).str.strip().str.casefold()
                == selected_store.casefold()]

    if df.empty:
        raise ValueError("No demand history found for the selected product/store.")

    result = (
        df.groupby("date", as_index=False)
        .agg(quantity=("quantity", "sum"), price=("price", "mean"),
             discount=("discount", "mean"))
        .sort_values("date")
        .reset_index(drop=True)
    )
    result["product"] = str(product or "ALL")
    result["store"] = str(selected_store or "ALL")
    return result[["date", "quantity", "product", "store", "price", "discount"]]


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please select a CSV or Excel file.")

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Upload CSV, XLSX or XLS.")

    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    total_bytes = 0

    try:
        with file_path.open("wb") as destination:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="File is too large. Please upload a file under 50 MB.",
                    )
                destination.write(chunk)
    except Exception:
        file_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    try:
        data, _source_metadata = await run_in_threadpool(adapt_dataset, file_path)
        required = {"date", "quantity", "product", "store", "price", "discount"}
        missing = required.difference(data.columns)
        if missing:
            raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
        if data.empty:
            raise ValueError("The uploaded dataset contains no usable rows.")

        products = sorted(data["product"].dropna().astype(str).unique().tolist())
        stores = sorted(data["store"].dropna().astype(str).unique().tolist())
        insights_result = await run_in_threadpool(build_insights, data)

        metadata = {
            "filename": file.filename,
            "rows": int(len(data)),
            "products": int(data["product"].nunique()),
            "stores": int(data["store"].nunique()),
            "start_date": str(pd.to_datetime(data["date"]).min().date()),
            "end_date": str(pd.to_datetime(data["date"]).max().date()),
        }
        session_id = create_session(data, metadata)

        preview = data.head(10).copy()
        preview["date"] = preview["date"].astype(str)
        logger.info("Dataset uploaded: rows=%s products=%s stores=%s",
                    len(data), len(products), len(stores))
        return {
            "success": True,
            "session_id": session_id,
            "metadata": metadata,
            "products": products,
            "stores": stores,
            "preview": preview.to_dict(orient="records"),
            "insights": insights_result,
        }
    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        logger.exception("Dataset processing failed")
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Invalid dataset: {str(exc)}") from exc


@app.post("/api/forecast")
async def forecast(request: ForecastRequest):
    _validate_horizon(request.horizon)
    try:
        session = get_session(request.session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session expired. Please upload the dataset again.") from exc

    try:
        data = session["data"].copy()
        data["product"] = data["product"].astype(str).str.strip()
        data["store"] = data["store"].astype(str).str.strip()

        product = str(request.product or data["product"].iloc[0]).strip()
        store = str(request.store or "All Stores").strip()
        product_mask = data["product"].str.casefold() == product.casefold()
        filtered = data.loc[product_mask].copy()

        selected_store = _normalise_all_store(store)
        if selected_store:
            filtered = filtered[
                filtered["store"].str.casefold() == selected_store.casefold()
            ]

        if filtered.empty:
            raise ValueError("No demand history found for the selected product/store.")

        history = (
            filtered.groupby(["date", "product", "store"], as_index=False)
            .agg(quantity=("quantity", "sum"), price=("price", "mean"),
                 discount=("discount", "mean"))
            .sort_values("date")
            .reset_index(drop=True)
        )

        # Aggregate to one row per date when the user selected all stores.
        if history["date"].duplicated().any():
            history = (
                history.groupby("date", as_index=False)
                .agg(quantity=("quantity", "sum"), price=("price", "mean"),
                     discount=("discount", "mean"), product=("product", "first"),
                     store=("store", "first"))
                .sort_values("date")
                .reset_index(drop=True)
            )
            history["store"] = store

        if len(history) < 5:
            raise ValueError(
                f"Not enough historical data: only {len(history)} time points found."
            )

        # Model fitting/prediction runs outside the ASGI event loop.
        result = await run_in_threadpool(recursive_forecast, history, request.horizon)
        forecast_df = result.get("forecast")
        if not isinstance(forecast_df, pd.DataFrame) or "forecast" not in forecast_df.columns:
            raise ValueError("Forecast model returned an invalid forecast dataframe.")

        inventory = await run_in_threadpool(
            calculate_inventory,
            history["quantity"].values,
            forecast_df["forecast"].values,
            current_stock=request.current_stock,
            lead_time_days=request.lead_time_days,
            safety_stock_days=request.safety_stock_days,
        )

        forecast_rows = forecast_df.copy()
        forecast_rows["date"] = forecast_rows["date"].astype(str)
        history_rows = history.tail(120).copy()
        history_rows["date"] = history_rows["date"].astype(str)

        return {
            "success": True,
            "product": product,
            "store": store,
            "horizon": request.horizon,
            "model": result.get("model"),
            "segment": result.get("segment"),
            "frequency": result.get("frequency"),
            "rows_used": result.get("rows_used"),
            "metrics": result.get("selected_metrics", {}),
            "model_metrics": result.get("model_metrics", {}),
            "inventory": inventory,
            "forecast": forecast_rows.to_dict(orient="records"),
            "history": history_rows[["date", "quantity"]].to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Forecast request failed")
        # A genuine server-side model/runtime failure should not be mislabeled as a 400.
        raise HTTPException(
            status_code=500,
            detail=f"Forecast failed ({type(exc).__name__}). Check server logs for details.",
        ) from exc


@app.post("/api/compare")
async def compare_products(request: CompareRequest):
    _validate_horizon(request.horizon)
    try:
        session = get_session(request.session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session expired. Please upload the dataset again.") from exc

    try:
        data = session["data"]
        results = []
        for product in [request.product1, request.product2]:
            history = select_series(data, product, request.store or "ALL")
            if len(history) < 5:
                raise ValueError(f"Not enough historical data for product '{product}'.")
            result = await run_in_threadpool(recursive_forecast, history, request.horizon)
            forecast_df = result["forecast"]
            results.append({
                "product": product,
                "model": result.get("model"),
                "segment": result.get("segment"),
                "forecast": (
                    forecast_df[["date", "forecast"]]
                    .assign(date=lambda frame: frame["date"].astype(str))
                    .to_dict(orient="records")
                ),
            })
        return {"success": True, "products": results}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Compare request failed")
        raise HTTPException(
            status_code=500,
            detail=f"Compare failed ({type(exc).__name__}). Check server logs for details.",
        ) from exc


@app.get("/api/insights/{session_id}")
async def insights(session_id: str):
    try:
        session = get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session expired. Please upload the dataset again.") from exc
    try:
        return await run_in_threadpool(build_insights, session["data"])
    except Exception as exc:
        logger.exception("Insights request failed")
        raise HTTPException(status_code=500, detail="Unable to build insights. Check server logs.") from exc


def build_insights(data):
    product_totals = data.groupby("product")["quantity"].sum().sort_values(ascending=False)
    segments = {}
    for product in data["product"].unique():
        product_data = data[data["product"] == product]
        series = product_data.groupby("date")["quantity"].sum().sort_index()
        segment = classify_demand(series.values)
        segments[segment] = segments.get(segment, 0) + 1

    return {
        "total_demand": round(float(data["quantity"].sum()), 2),
        "average_demand": round(float(data["quantity"].mean()), 2),
        "max_demand": round(float(data["quantity"].max()), 2),
        "top_products": [
            {"product": str(index), "demand": round(float(value), 2)}
            for index, value in product_totals.head(10).items()
        ],
        "segments": segments,
    }
