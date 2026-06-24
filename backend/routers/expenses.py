from fastapi import APIRouter
from main import app_state
from cache.redis_client import get_api_cache, set_api_cache
from utils import safe_num

router = APIRouter()

MONTH_LABELS = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "may": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "oct": "October", "nov": "November", "dec": "December",
}


@router.get("/expenses")
async def get_expenses():
    cached = await get_api_cache("expenses")
    if cached:
        return cached

    data = app_state.get("data", {})

    budget_flow    = []
    activity_totals: dict[str, dict] = {}
    expenses_by_month: dict[str, list] = {}

    for month_key, mdata in data.items():
        exp   = mdata.get("expense", {})
        ae_df = exp.get("activity_exp")

        budget_flow.append({
            "month":              MONTH_LABELS.get(month_key, month_key.title()),
            "opening_balance_ugx": safe_num(exp.get("opening_balance_ugx", 0)),
            "received_ugx":       safe_num(exp.get("total_received_ugx", 0)),
            "spent_ugx":          safe_num(exp.get("total_spent_ugx", 0)),
            "balance_ugx":        safe_num(exp.get("balance_ugx", 0)),
            "opening_balance_eur": safe_num(exp.get("opening_balance_eur", 0)),
            "received_eur":       safe_num(exp.get("total_received_eur", 0)),
            "spent_eur":          safe_num(exp.get("total_spent_eur", 0)),
            "balance_eur":        safe_num(exp.get("balance_eur", 0)),
        })

        month_exp_list = []
        if ae_df is not None and not ae_df.empty:
            for _, r in ae_df.iterrows():
                act     = r.get("Activity", "VISIT")
                amt_ugx = safe_num(r.get("Amount_UGX", 0))
                if act not in activity_totals:
                    activity_totals[act] = {"activity": act, "amount_ugx": 0.0, "amount_eur": 0.0}
                activity_totals[act]["amount_ugx"] += amt_ugx
                activity_totals[act]["amount_eur"]  += safe_num(r.get("Amount_EUR", 0))

                month_exp_list.append({
                    "sn":                int(safe_num(r.get("SN", 0))),
                    "doctor":            r.get("Doctor", ""),
                    "hospital":          r.get("Hospital", ""),
                    "speciality":        r.get("Speciality", ""),
                    "activity":          act,
                    "activity_id":       r.get("Activity_ID", ""),
                    "products":          r.get("Products", ""),
                    "amount_ugx":        amt_ugx,
                    "amount_eur":        safe_num(r.get("Amount_EUR", 0)),
                    "responsible":       r.get("Responsible", ""),
                    "sales_outcome":     r.get("Sales_Outcome", []),
                    "sales_outcome_eur": safe_num(r.get("Sales_Outcome_EUR", 0)),
                    "num_visits":        int(safe_num(r.get("Num_Visits", 0))),
                })
        expenses_by_month[month_key] = month_exp_list

    result = {
        "budget_flow":          budget_flow,
        "activity_type_totals": sorted(activity_totals.values(), key=lambda x: x["amount_ugx"], reverse=True),
        "expenses_by_month":    expenses_by_month,
    }

    await set_api_cache("expenses", result)
    return result
