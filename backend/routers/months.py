import pandas as pd
from fastapi import APIRouter, HTTPException
from main import app_state
from cache.redis_client import get_api_cache, set_api_cache
from utils import safe_num
from name_map import mr_display_name

router = APIRouter()

MONTH_LABELS = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "may": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "oct": "October", "nov": "November", "dec": "December",
}


@router.get("/months/{month}")
async def get_month(month: str):
    cache_key = f"months:{month}"
    cached = await get_api_cache(cache_key)
    if cached:
        return cached

    data = app_state.get("data", {})
    if month not in data:
        raise HTTPException(status_code=404, detail=f"Month {month!r} not loaded")

    mdata     = data[month]
    sales_df  = mdata.get("sales", {}).get("current")
    proj_df   = mdata.get("projection", {}).get("projection")
    exp       = mdata.get("expense", {})
    monthly   = mdata.get("monthly", {}).get("delegates")
    tour_df   = mdata.get("tour")
    visits_df = mdata.get("visits")
    ae_df     = mdata.get("expense", {}).get("activity_exp")

    total_sales  = safe_num(sales_df["TOTAL_VALUE_EUR"].sum())  if sales_df  is not None and not sales_df.empty  and "TOTAL_VALUE_EUR"  in sales_df.columns  else 0.0
    tablet_sales = safe_num(sales_df[sales_df["Category"] == "TABLET"]["TOTAL_VALUE_EUR"].sum()) if sales_df is not None and not sales_df.empty and "Category" in sales_df.columns else 0.0
    inj_sales    = safe_num(sales_df[sales_df["Category"] == "INJECTABLE"]["TOTAL_VALUE_EUR"].sum()) if sales_df is not None and not sales_df.empty and "Category" in sales_df.columns else 0.0
    total_target = safe_num(proj_df["Target_Value_EUR"].sum())  if proj_df   is not None and not proj_df.empty   and "Target_Value_EUR" in proj_df.columns    else 0.0
    achievement  = (total_sales / total_target * 100) if total_target else 0.0

    total_visits   = len(visits_df[visits_df["Visit_Date"].notna()]) if visits_df is not None and not visits_df.empty and "Visit_Date" in visits_df.columns else 0
    prescriber     = int(safe_num(monthly["Prescriber"].sum()))    if monthly is not None and not monthly.empty and "Prescriber"    in monthly.columns else 0
    non_prescriber = int(safe_num(monthly["NonPrescriber"].sum())) if monthly is not None and not monthly.empty and "NonPrescriber" in monthly.columns else 0
    pharmacy       = int(safe_num(monthly["PharmacyCalls"].sum())) if monthly is not None and not monthly.empty and "PharmacyCalls" in monthly.columns else 0
    drs_conv       = int(safe_num(monthly["DrsConverted"].sum()))  if monthly is not None and not monthly.empty and "DrsConverted"  in monthly.columns else 0
    days_worked    = safe_num(monthly["DaysWorked"].sum())         if monthly is not None and not monthly.empty and "DaysWorked"    in monthly.columns else 1.0
    avg_visits     = total_visits / days_worked if days_worked else 0.0

    kpis = {
        "total_sales_eur":       total_sales,
        "tablet_sales_eur":      tablet_sales,
        "injectable_sales_eur":  inj_sales,
        "total_target_eur":      total_target,
        "achievement_pct":       achievement,
        "total_visits":          total_visits,
        "prescriber_calls":      prescriber,
        "non_prescriber_calls":  non_prescriber,
        "pharmacy_calls":        pharmacy,
        "drs_converted":         drs_conv,
        "avg_visits_day":        avg_visits,
        "activity_spent_ugx":    safe_num(exp.get("total_spent_ugx", 0)),
        "activity_spent_eur":    safe_num(exp.get("total_spent_eur", 0)),
        "activity_received_ugx": safe_num(exp.get("total_received_ugx", 0)),
        "activity_received_eur": safe_num(exp.get("total_received_eur", 0)),
        "opening_balance_ugx":   safe_num(exp.get("opening_balance_ugx", 0)),
        "opening_balance_eur":   safe_num(exp.get("opening_balance_eur", 0)),
    }

    product_sales = []
    if sales_df is not None and not sales_df.empty:
        proj_map: dict[str, float] = {}
        proj_map_units: dict[str, int] = {}
        if proj_df is not None and not proj_df.empty and "Product" in proj_df.columns:
            for _, r in proj_df.iterrows():
                proj_map[r["Product"]] = safe_num(r.get("Target_Value_EUR", 0))
                proj_map_units[r["Product"]] = int(safe_num(r.get("Target_Units", 0)))
        for _, r in sales_df.sort_values("TOTAL_VALUE_EUR", ascending=False).iterrows():
            prod = r.get("Product", "")
            product_sales.append({
                "product":      prod,
                "sales_eur":    safe_num(r.get("TOTAL_VALUE_EUR", 0)),
                "target_eur":   proj_map.get(prod, 0.0),
                "units":        int(safe_num(r.get("TOTAL_SALES", 0))),
                "target_units": proj_map_units.get(prod, 0),
                "closing":      int(safe_num(r.get("CLOSING_STOCK", 0))),
            })

    from constants import DISTRIBUTORS
    distributor_sales = []

    delegate_table = []
    if monthly is not None and not monthly.empty:
        for _, r in monthly.iterrows():
            del_id   = r.get("Delegate", "")
            del_name = mr_display_name(del_id) if del_id else r.get("Delegate_Raw", "")
            orders   = safe_num(r.get("TotalOrders", 0))
            ctc_val  = safe_num(r.get("CTC", 0))
            delegate_table.append({
                "name":           del_name,
                "territory":      r.get("Territory", ""),
                "total_calls":    int(safe_num(r.get("TotalCalls", 0))),
                "prescriber":     int(safe_num(r.get("Prescriber", 0))),
                "non_prescriber": int(safe_num(r.get("NonPrescriber", 0))),
                "pharmacy":       int(safe_num(r.get("PharmacyCalls", 0))),
                "drs_converted":  int(safe_num(r.get("DrsConverted", 0))),
                "days_worked":    int(safe_num(r.get("DaysWorked", 0))),
                "avg_per_day":    safe_num(r.get("AvgCallsPerDay", 0)),
                "orders_eur":     orders or None,
                "ctc_eur":        ctc_val or None,
                "ctc_ratio":      (ctc_val / orders) if orders else None,
                "dr_in_list":     r.get("DrInList"),
                "listed_covered": r.get("ListedDRCovered"),
                "pct_listed":     r.get("PctDRCovered"),
            })

    activity_expenses = []
    if ae_df is not None and not ae_df.empty:
        for _, r in ae_df.iterrows():
            activity_expenses.append({
                "sn":                int(safe_num(r.get("SN", 0))),
                "doctor":            r.get("Doctor", ""),
                "hospital":          r.get("Hospital", ""),
                "speciality":        r.get("Speciality", ""),
                "activity":          r.get("Activity", ""),
                "activity_id":       r.get("Activity_ID", ""),
                "products":          r.get("Products", ""),
                "amount_ugx":        safe_num(r.get("Amount_UGX", 0)),
                "amount_eur":        safe_num(r.get("Amount_EUR", 0)),
                "responsible":       r.get("Responsible", ""),
                "sales_outcome":     r.get("Sales_Outcome", []),
                "sales_outcome_eur": safe_num(r.get("Sales_Outcome_EUR", 0)),
                "num_visits":        int(safe_num(r.get("Num_Visits", 0))),
            })

    tour_plan = {"summary": {}, "by_delegate": [], "entries": [], "entries_by_delegate": {}}
    if tour_df is not None and not tour_df.empty:
        if "Planned_Area" in tour_df.columns:
            # Match "public holiday" loosely since the source data has typos
            # (e.g. "Public holday") and inconsistent casing/spacing.
            normalized = tour_df["Planned_Area"].astype(str).str.lower().str.replace(r"[^a-z]", "", regex=True)
            non_working_mask = normalized.str.startswith("publichol") | (normalized == "weekoff")
        else:
            non_working_mask = pd.Series(False, index=tour_df.index)
        working_df = tour_df[~non_working_mask]

        total_planned = len(working_df)
        covered_count = int(working_df["Covered"].sum()) if "Covered" in working_df.columns else 0
        joint_count   = int((tour_df["Joint_Working"].str.strip() != "").sum()) if "Joint_Working" in tour_df.columns else 0

        tour_plan["summary"] = {
            "total": total_planned, "covered": covered_count,
            "uncovered": total_planned - covered_count,
            "coverage_pct": (covered_count / total_planned * 100) if total_planned else 0.0,
            "delegates_active": tour_df["MR"].nunique() if "MR" in tour_df.columns else 0,
            "joint_working": joint_count,
        }

        by_delegate = []
        for mr_id, grp in working_df.groupby("MR"):
            planned = len(grp)
            covered = int(grp["Covered"].sum()) if "Covered" in grp.columns else 0
            by_delegate.append({
                "mr": mr_display_name(mr_id), "mr_id": mr_id,
                "planned": planned, "covered": covered, "uncovered": planned - covered,
                "coverage_pct": (covered / planned * 100) if planned else 0.0,
            })
        tour_plan["by_delegate"] = by_delegate

        entries = []
        for _, r in tour_df.iterrows():
            entries.append({
                "date":          r["Date"].strftime("%Y-%m-%d") if pd.notna(r["Date"]) else "",
                "mr":            mr_display_name(r.get("MR", "")),
                "planned_area":  r.get("Planned_Area", ""),
                "actual_area":   r.get("Actual_Area", ""),
                "covered":       bool(r.get("Covered", False)),
                "joint_working": r.get("Joint_Working", ""),
            })
        tour_plan["entries"] = entries

        by_del_entries: dict = {}
        for mr_id, grp in tour_df.groupby("MR"):
            mr_name = mr_display_name(mr_id)
            by_del_entries[mr_name] = [
                {"date": r["Date"].strftime("%Y-%m-%d") if pd.notna(r["Date"]) else "",
                 "mr": mr_name, "planned_area": r.get("Planned_Area", ""),
                 "actual_area": r.get("Actual_Area", ""), "covered": bool(r.get("Covered", False)),
                 "joint_working": r.get("Joint_Working", "")}
                for _, r in grp.iterrows()
            ]
        tour_plan["entries_by_delegate"] = by_del_entries

    listed_covered_map = {}
    if monthly is not None and not monthly.empty:
        listed_covered_map = {r.get("Delegate", ""): r.get("ListedDRCovered") for _, r in monthly.iterrows()}

    visit_tracker = {"by_delegate": []}
    if visits_df is not None and not visits_df.empty:
        by_delegate_visits = []
        for mr_id, grp in visits_df.groupby("MR_ID"):
            mr_name = mr_display_name(mr_id) if mr_id else grp.iloc[0].get("MR", mr_id)
            visits_with_date = grp[grp["Visit_Date"].notna()] if "Visit_Date" in grp.columns else grp
            visits = [{"date": r["Visit_Date"].strftime("%Y-%m-%d") if pd.notna(r.get("Visit_Date")) else "",
                       "doctor": r.get("Doctor", ""), "speciality": r.get("Speciality", ""), "clinic": r.get("Clinic", ""),
                       "listed": r.get("Listed", "")}
                      for _, r in visits_with_date.iterrows()]
            by_delegate_visits.append({
                "mr": mr_name, "mr_id": mr_id,
                "total_visits": len(visits_with_date),
                "listed_covered": listed_covered_map.get(mr_id),
                "visits": visits,
            })
        visit_tracker["by_delegate"] = by_delegate_visits

    result = {
        "month":             month,
        "label":             MONTH_LABELS.get(month, month.title()),
        "kpis":              kpis,
        "product_sales":     product_sales,
        "distributor_sales": distributor_sales,
        "delegate_table":    delegate_table,
        "activity_expenses": activity_expenses,
        "tour_plan":         tour_plan,
        "visit_tracker":     visit_tracker,
    }

    await set_api_cache(cache_key, result)
    return result
