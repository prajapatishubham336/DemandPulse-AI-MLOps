import numpy as np


def calculate_inventory(
    history,
    forecast,
    current_stock=0,
    lead_time_days=7,
    safety_stock_days=3
):
    history = np.asarray(history, dtype=float)
    forecast = np.asarray(forecast, dtype=float)

    avg_daily_demand = float(
        np.mean(history[-min(30, len(history)):])
    ) if len(history) else 0.0

    if avg_daily_demand <= 0:
        avg_daily_demand = float(np.mean(forecast)) if len(forecast) else 0.0

    lead_time_demand = avg_daily_demand * lead_time_days
    safety_stock = avg_daily_demand * safety_stock_days
    reorder_point = lead_time_demand + safety_stock

    forecast_demand = float(np.sum(forecast))
    reorder_quantity = max(0, int(np.ceil(forecast_demand + safety_stock - current_stock)))
    stock_after_forecast = current_stock - forecast_demand

    if current_stock <= 0:
        status = "Out of Stock"
        risk = "Critical"
    elif current_stock <= reorder_point:
        status = "Reorder Now"
        risk = "High"
    elif stock_after_forecast < 0:
        status = "Stock-out Risk"
        risk = "High"
    elif stock_after_forecast <= safety_stock:
        status = "Low Stock"
        risk = "Medium"
    else:
        status = "Healthy"
        risk = "Low"

    return {
        "current_stock": round(float(current_stock), 2),
        "average_daily_demand": round(avg_daily_demand, 2),
        "lead_time_demand": round(lead_time_demand, 2),
        "safety_stock": round(safety_stock, 2),
        "reorder_point": round(reorder_point, 2),
        "reorder_quantity": reorder_quantity,
        "forecast_demand": round(forecast_demand, 2),
        "stock_after_forecast": round(stock_after_forecast, 2),
        "status": status,
        "risk": risk
    }