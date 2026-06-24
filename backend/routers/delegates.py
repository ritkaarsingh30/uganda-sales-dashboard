from fastapi import APIRouter
from main import app_state
from cache.redis_client import get_api_cache, set_api_cache
from utils import safe_num
from name_map import mr_display_name, mr_short_name
from constants import _NON_MR_IDS

router = APIRouter()


@router.get("/delegates")
async def get_delegates():
    cached = await get_api_cache("delegates")
    if cached:
        return cached

    data = app_state.get("data", {})
    result_map: dict[str, dict] = {}

    for month_key, mdata in data.items():
        monthly   = mdata.get("monthly", {}).get("delegates")
        tour_df   = mdata.get("tour")
        if monthly is None or monthly.empty:
            continue

        for _, r in monthly.iterrows():
            del_id = r.get("Delegate", "")
            if del_id in _NON_MR_IDS:
                continue

            if del_id not in result_map:
                result_map[del_id] = {
                    "id":           del_id,
                    "display_name": mr_display_name(del_id),
                    "short_name":   mr_short_name(del_id),
                    "territory":    r.get("Territory", ""),
                    "months":       {},
                    "q1": {"calls": 0, "prescriber": 0, "pharmacy": 0, "drs_converted": 0,
                           "days_worked": 0, "days_target": 0, "orders_eur": 0.0, "ctc_eur": 0.0,
                           "tour_planned": 0, "tour_covered": 0},
                }

            orders  = safe_num(r.get("TotalOrders", 0))
            ctc_val = safe_num(r.get("CTC", 0))

            tour_planned = tour_covered = 0
            if tour_df is not None and not tour_df.empty and "MR" in tour_df.columns:
                mr_tour      = tour_df[tour_df["MR"] == del_id]
                tour_planned = len(mr_tour)
                tour_covered = int(mr_tour["Covered"].sum()) if "Covered" in mr_tour.columns else 0

            month_entry = {
                "calls":            int(safe_num(r.get("TotalCalls", 0))),
                "prescriber":       int(safe_num(r.get("Prescriber", 0))),
                "pharmacy":         int(safe_num(r.get("PharmacyCalls", 0))),
                "drs_converted":    int(safe_num(r.get("DrsConverted", 0))),
                "days_worked":      int(safe_num(r.get("DaysWorked", 0))),
                "days_target":      int(safe_num(r.get("DaysTarget", 0))),
                "avg_calls_day":    safe_num(r.get("AvgCallsPerDay", 0)),
                "orders_eur":       orders,
                "ctc_eur":          ctc_val,
                "ctc_ratio":        (ctc_val / orders) if orders else None,
                "days_utilization": (safe_num(r.get("DaysWorked", 0)) / safe_num(r.get("DaysTarget", 1))) if safe_num(r.get("DaysTarget", 0)) else None,
                "tour_planned":     tour_planned,
                "tour_covered":     tour_covered,
                "tour_coverage_pct": (tour_covered / tour_planned * 100) if tour_planned else None,
                "dr_in_list":       r.get("DrInList"),
                "listed_covered":   r.get("ListedDRCovered"),
                "pct_listed":       r.get("PctDRCovered"),
            }
            result_map[del_id]["months"][month_key] = month_entry

            q = result_map[del_id]["q1"]
            q["calls"]         += month_entry["calls"]
            q["prescriber"]    += month_entry["prescriber"]
            q["pharmacy"]      += month_entry["pharmacy"]
            q["drs_converted"] += month_entry["drs_converted"]
            q["days_worked"]   += month_entry["days_worked"]
            q["days_target"]   += month_entry["days_target"]
            q["orders_eur"]    += orders
            q["ctc_eur"]       += ctc_val
            q["tour_planned"]  += tour_planned
            q["tour_covered"]  += tour_covered

    for entry in result_map.values():
        q = entry["q1"]
        q["ctc_ratio"]         = (q["ctc_eur"] / q["orders_eur"]) if q["orders_eur"] else None
        q["days_utilization"]  = (q["days_worked"] / q["days_target"]) if q["days_target"] else None
        q["tour_coverage_pct"] = (q["tour_covered"] / q["tour_planned"] * 100) if q["tour_planned"] else None
        q["conversion_pct"]    = (q["drs_converted"] / q["prescriber"] * 100) if q["prescriber"] else None

    delegates = sorted(result_map.values(), key=lambda x: x["display_name"])
    total_orders = sum(d["q1"]["orders_eur"] for d in delegates)
    total_ctc    = sum(d["q1"]["ctc_eur"]    for d in delegates)

    result = {
        "q1_summary": {
            "total_calls":       sum(d["q1"]["calls"] for d in delegates),
            "total_orders_eur":  total_orders,
            "total_ctc_eur":     total_ctc,
            "overall_ctc_ratio": (total_ctc / total_orders) if total_orders else None,
        },
        "delegates": delegates,
    }

    await set_api_cache("delegates", result)
    return result
