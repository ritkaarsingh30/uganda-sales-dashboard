from fastapi import APIRouter
from main import app_state
from cache.redis_client import get_api_cache, set_api_cache
from utils import safe_num
from constants import _NON_MR_IDS

router = APIRouter()

MONTH_LABELS = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "may": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "oct": "October", "nov": "November", "dec": "December",
}

MONTH_ORDER = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]


@router.get("/overview")
async def get_overview():
    cached = await get_api_cache("overview")
    if cached:
        return cached

    data               = app_state.get("data", {})
    annual_projections = app_state.get("annual_projections", {})

    month_sales: dict[str, float] = {}
    month_proj: dict[str, float] = {}
    month_achievement: dict[str, float] = {}
    month_visits: dict[str, int] = {}
    month_drs: dict[str, int] = {}
    month_avg_calls: dict[str, float] = {}
    month_comparison = []
    product_totals: dict[str, float] = {}

    for month_key, mdata in data.items():
        sales_df = mdata.get("sales", {}).get("current")
        proj     = mdata.get("projection", {}).get("projection")
        exp      = mdata.get("expense", {})
        monthly  = mdata.get("monthly", {}).get("delegates")

        total_sales = total_proj = 0.0

        if sales_df is not None and not sales_df.empty and "TOTAL_VALUE_EUR" in sales_df.columns:
            total_sales = safe_num(sales_df["TOTAL_VALUE_EUR"].sum())
            for _, row in sales_df.iterrows():
                prod = row.get("Product", "")
                product_totals[prod] = product_totals.get(prod, 0.0) + safe_num(row.get("TOTAL_VALUE_EUR", 0))

        if proj is not None and not proj.empty and "Target_Value_EUR" in proj.columns:
            total_proj = safe_num(proj["Target_Value_EUR"].sum())

        month_sales[month_key]       = total_sales
        month_proj[month_key]        = total_proj
        month_achievement[month_key] = (total_sales / total_proj * 100) if total_proj else 0.0

        visits_df    = mdata.get("visits")
        visits_count = len(visits_df[visits_df["Visit_Date"].notna()]) if visits_df is not None and not visits_df.empty and "Visit_Date" in visits_df.columns else 0
        month_visits[month_key] = visits_count

        drs_conv  = 0
        avg_calls = 0.0
        active_mrs = 0
        if monthly is not None and not monthly.empty:
            drs_conv  = int(safe_num(monthly["DrsConverted"].sum())) if "DrsConverted" in monthly.columns else 0
            avg_calls = safe_num(monthly["AvgCallsPerDay"].mean())   if "AvgCallsPerDay" in monthly.columns else 0.0
            if "Delegate" in monthly.columns:
                active_mrs = int(monthly["Delegate"].apply(lambda x: x not in _NON_MR_IDS).sum())
        month_drs[month_key]       = drs_conv
        month_avg_calls[month_key] = avg_calls

        top_prod = ""
        if sales_df is not None and not sales_df.empty and "TOTAL_VALUE_EUR" in sales_df.columns:
            idx = sales_df["TOTAL_VALUE_EUR"].idxmax()
            top_prod = sales_df.loc[idx, "Product"] if idx is not None else ""

        ae_df = mdata.get("expense", {}).get("activity_exp")
        activity_spent_eur = safe_num(ae_df["Amount_EUR"].sum()) if ae_df is not None and not ae_df.empty and "Amount_EUR" in ae_df.columns else 0.0

        month_comparison.append({
            "key":               month_key,
            "month":             MONTH_LABELS.get(month_key, month_key.title()),
            "sales":             total_sales,
            "projection":        total_proj,
            "achievement":       month_achievement[month_key],
            "visits":            visits_count,
            "prescriber_calls":  int(safe_num(monthly["Prescriber"].sum()))    if monthly is not None and not monthly.empty and "Prescriber"    in monthly.columns else 0,
            "pharmacy_calls":    int(safe_num(monthly["PharmacyCalls"].sum()))  if monthly is not None and not monthly.empty and "PharmacyCalls" in monthly.columns else 0,
            "drs_converted":     drs_conv,
            "avg_visits_day":    avg_calls,
            "active_mrs":        active_mrs,
            "activity_spent_eur": activity_spent_eur,
            "top_product":       top_prod,
        })

    total_sales_all = sum(month_sales.values())
    annual_target   = sum(month_proj.values())
    best_month      = max(month_sales, key=month_sales.get) if month_sales else ""
    top_prod_all    = max(product_totals, key=product_totals.get) if product_totals else ""

    # Month-over-month change (compare two most recent consecutive months)
    sorted_months = sorted(month_sales.keys(), key=lambda m: MONTH_ORDER.index(m) if m in MONTH_ORDER else 99)
    mom_sales_change_eur = mom_sales_change_pct = mom_visits_change_pct = None
    if len(sorted_months) >= 2:
        prev_m, latest_m = sorted_months[-2], sorted_months[-1]
        prev_s, latest_s = month_sales[prev_m], month_sales[latest_m]
        mom_sales_change_eur = round(latest_s - prev_s, 2)
        mom_sales_change_pct = round((latest_s - prev_s) / prev_s * 100, 1) if prev_s else None
        prev_v  = month_visits.get(prev_m, 0)
        latest_v = month_visits.get(latest_m, 0)
        mom_visits_change_pct = round((latest_v - prev_v) / prev_v * 100, 1) if prev_v else None

    # Add growth_pct to month_comparison (% change vs previous month in sorted order)
    month_comparison.sort(key=lambda e: MONTH_ORDER.index(e["key"]) if e["key"] in MONTH_ORDER else 99)
    prev_sales_for_growth = None
    for entry in month_comparison:
        if prev_sales_for_growth is not None and prev_sales_for_growth > 0:
            entry["growth_pct"] = round((entry["sales"] - prev_sales_for_growth) / prev_sales_for_growth * 100, 1)
        else:
            entry["growth_pct"] = None
        prev_sales_for_growth = entry["sales"]

    all_products_trend = []
    for prod in sorted(product_totals.keys()):
        entry = {"product": prod}
        for month_key, mdata in data.items():
            df = mdata.get("sales", {}).get("current")
            if df is not None and not df.empty and "Product" in df.columns:
                match = df[df["Product"] == prod]
                entry[month_key] = safe_num(match["TOTAL_VALUE_EUR"].sum()) if not match.empty else 0.0
            else:
                entry[month_key] = 0.0
        all_products_trend.append(entry)

    product_mix: dict[str, dict] = {}
    for month_key, mdata in data.items():
        df = mdata.get("sales", {}).get("current")
        tablet = injectable = 0.0
        if df is not None and not df.empty and "Category" in df.columns:
            tablet     = safe_num(df[df["Category"] == "TABLET"]["TOTAL_VALUE_EUR"].sum())
            injectable = safe_num(df[df["Category"] == "INJECTABLE"]["TOTAL_VALUE_EUR"].sum())
        product_mix[month_key] = {"tablet": tablet, "injectable": injectable}

    summary = {
        "total_sales_eur":        total_sales_all,
        "month_sales":            month_sales,
        "month_achievement_pct":  month_achievement,
        "annual_target_eur":      annual_target,
        "annual_achievement_pct": (total_sales_all / annual_target * 100) if annual_target else 0.0,
        "best_month":             best_month,
        "best_month_sales":       month_sales.get(best_month, 0.0),
        "top_product_all":        top_prod_all,
        "top_product_all_val":    product_totals.get(top_prod_all, 0.0),
        "total_visits":           month_visits,
        "total_visits_all":       sum(month_visits.values()),
        "drs_converted":          month_drs,
        "drs_converted_all":      sum(month_drs.values()),
        "avg_calls_per_day":      month_avg_calls,
        "mom_sales_change_eur":   mom_sales_change_eur,
        "mom_sales_change_pct":   mom_sales_change_pct,
        "mom_visits_change_pct":  mom_visits_change_pct,
    }

    result = {
        "q1_summary":         summary,
        "month_comparison":   month_comparison,
        "product_mix":        product_mix,
        "all_products_trend": all_products_trend,
        "months_loaded":      list(data.keys()),
    }

    await set_api_cache("overview", result)
    return result
