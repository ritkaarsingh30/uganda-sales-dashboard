from fastapi import APIRouter
from main import app_state
from cache.redis_client import get_api_cache, set_api_cache
from utils import safe_num

router = APIRouter()


@router.get("/products")
async def get_products():
    cached = await get_api_cache("products")
    if cached:
        return cached

    data               = app_state.get("data", {})
    annual_projections = app_state.get("annual_projections", {})

    month_sales: dict[str, float] = {}
    month_units: dict[str, int]   = {}
    product_trend: dict[str, dict] = {}
    product_closing: dict[str, float] = {}
    category_mix: dict[str, dict]  = {}

    for month_key, mdata in data.items():
        df = mdata.get("sales", {}).get("current")
        if df is None or df.empty:
            month_sales[month_key] = 0.0
            month_units[month_key] = 0
            continue

        month_sales[month_key] = safe_num(df["TOTAL_VALUE_EUR"].sum()) if "TOTAL_VALUE_EUR" in df.columns else 0.0
        month_units[month_key] = int(df["TOTAL_SALES"].sum())          if "TOTAL_SALES"     in df.columns else 0

        for _, r in df.iterrows():
            prod = r.get("Product", "")
            if prod not in product_trend:
                product_trend[prod] = {}
            product_trend[prod][month_key] = safe_num(r.get("TOTAL_VALUE_EUR", 0))
            closing = r.get("CLOSING_STOCK")
            if closing is not None:
                product_closing[prod] = safe_num(closing)

        tablet     = safe_num(df[df["Category"] == "TABLET"]["TOTAL_VALUE_EUR"].sum())     if "Category" in df.columns else 0.0
        injectable = safe_num(df[df["Category"] == "INJECTABLE"]["TOTAL_VALUE_EUR"].sum()) if "Category" in df.columns else 0.0
        category_mix[month_key] = {"tablet": tablet, "injectable": injectable}

    q1_trend = []
    for prod, months in sorted(product_trend.items()):
        entry = {"product": prod}
        entry.update(months)
        q1_trend.append(entry)

    all_prods = sorted(set(list(product_trend.keys()) + list(annual_projections.keys())))
    annual_vs = []
    for prod in all_prods:
        ytd = sum(product_trend.get(prod, {}).values())
        annual_vs.append({
            "product": prod,
            "annual_target": annual_projections.get(prod),
            "ytd_achieved": ytd,
            "closing_stock": product_closing.get(prod),
        })
    annual_vs.sort(key=lambda x: x["ytd_achieved"], reverse=True)

    result = {
        "q1_kpis": {
            "total_sales_eur": sum(month_sales.values()),
            "total_units":     sum(month_units.values()),
            "month_sales":     month_sales,
            "month_units":     month_units,
        },
        "q1_trend":     q1_trend,
        "annual_vs_q1": annual_vs,
        "category_mix": category_mix,
    }

    await set_api_cache("products", result)
    return result
