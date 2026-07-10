import re as _re

from fastapi import APIRouter
from rapidfuzz import fuzz

from main import app_state
from cache.redis_client import get_api_cache, set_api_cache
from utils import safe_num
from name_map import mr_display_name
from constants import UGX_TO_EUR

router = APIRouter()

FUZZY_DOC_THRESHOLD = 85


def _norm_doc(s):
    s = str(s).lower().strip()
    s = _re.sub(r'^dr[.\s]+', '', s)
    s = _re.sub(r'[^a-z\s]', '', s)
    return _re.sub(r'\s+', ' ', s).strip()


def _doc_words(s):
    return set(_norm_doc(s).split())


HOSPITAL_STOPWORDS = {
    'hospital', 'referral', 'rrh', 'national', 'specialist', 'medical',
    'clinic', 'center', 'centre', 'regional', 'general',
}


def _norm_hospital(s):
    s = str(s).lower().strip()
    s = _re.sub(r'[^a-z\s]', ' ', s)
    words = [w for w in s.split() if w and w not in HOSPITAL_STOPWORDS]
    return ' '.join(words)


def _hosp_match(p, a):
    p, a = str(p or '').strip(), str(a or '').strip()
    if not p or not a:
        return None
    np, na = _norm_hospital(p), _norm_hospital(a)
    if not np or not na:
        return None
    if np == na:
        return True
    pw, aw = set(np.split()), set(na.split())
    if any(len(w) >= 4 for w in pw & aw):
        return True
    return fuzz.ratio(np, na) >= 60


SPECIALITY_GROUPS = {
    'phy': 'physician', 'physician': 'physician',
    'nephr': 'nephrology', 'nephro': 'nephrology', 'nephrologist': 'nephrology',
    'neuro': 'neurology', 'neurologist': 'neurology',
    'neurosurgeon': 'neurosurgery', 'neurosurgery': 'neurosurgery',
    'uro': 'urology', 'urologist': 'urology',
    'ortho': 'orthopedics', 'orthopedic': 'orthopedics', 'orthopaedic': 'orthopedics',
    'gp': 'general practice',
    'mo': 'medical officer',
    'sho': 'senior house officer',
    'pharmacist': 'pharmacist',
}


def _spec_group(s):
    s = str(s or '').strip().lower()
    s = _re.sub(r'[^a-z\s]', '', s)
    return SPECIALITY_GROUPS.get(s, s)


def _spec_match(p, a):
    p, a = str(p or '').strip(), str(a or '').strip()
    if not p or not a:
        return None
    return _spec_group(p) == _spec_group(a)


def _corroborated(p_row, a_row):
    hosp = _hosp_match(p_row.get("Hospital", ""), a_row.get("Hospital", ""))
    spec = _spec_match(p_row.get("Speciality", ""), a_row.get("Speciality", ""))
    signals = [s for s in (hosp, spec) if s is not None]
    if not signals:
        return True
    return any(signals)


MONTH_LABELS = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "may": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "oct": "October", "nov": "November", "dec": "December",
}


def _match_activities(plan_df, actual_df):
    matched = []
    planned_not_done = []
    unplanned_done = []

    if plan_df is None or plan_df.empty:
        if actual_df is not None and not actual_df.empty:
            for _, r in actual_df.iterrows():
                unplanned_done.append({
                    "doctor": r.get("Doctor", ""), "hospital": r.get("Hospital", ""),
                    "speciality": r.get("Speciality", ""), "area": "",
                    "delegate": mr_display_name(r.get("MR_IDs", "").split(",")[0]) if r.get("MR_IDs") else "",
                    "activity": r.get("Activity", ""), "activity_id": r.get("Activity_ID", ""),
                    "focus_products": r.get("Products", ""),
                    "planned_ugx": 0.0, "planned_eur": 0.0,
                    "actual_ugx": safe_num(r.get("Amount_UGX", 0)),
                    "actual_eur": safe_num(r.get("Amount_EUR", 0)),
                    "variance_ugx": safe_num(r.get("Amount_UGX", 0)),
                    "sales_outcome": r.get("Sales_Outcome", []),
                    "sales_outcome_eur": safe_num(r.get("Sales_Outcome_EUR", 0)),
                    "has_outcome": bool(r.get("Sales_Outcome")),
                    "num_visits": int(safe_num(r.get("Num_Visits", 0))),
                    "responsible": r.get("Responsible", ""), "status": "unplanned",
                })
        return matched, planned_not_done, unplanned_done

    used_actual = set()
    plan_to_actual = {}

    # Pass 1: exact normalized doctor-name match (first available wins).
    if actual_df is not None and not actual_df.empty:
        for p_idx, p_row in plan_df.iterrows():
            p_doc = _norm_doc(p_row.get("Doctor", ""))
            for a_idx, a_row in actual_df.iterrows():
                if a_idx in used_actual:
                    continue
                if _norm_doc(a_row.get("Doctor", "")) == p_doc:
                    used_actual.add(a_idx)
                    plan_to_actual[p_idx] = a_idx
                    break

    # Pass 2: remaining doctors — resolve word-reordering, partial names, and
    # spelling typos (e.g. "Kyalesubula Robert" vs "Robert Kalesubla") via a
    # word-set/subset check first (zero false-positive risk), falling back to
    # fuzzy token-sort matching for the rest. Candidates are scored and
    # assigned highest-confidence-first so the best pairing wins.
    candidates = []
    if actual_df is not None and not actual_df.empty:
        for p_idx, p_row in plan_df.iterrows():
            if p_idx in plan_to_actual:
                continue
            p_doc = p_row.get("Doctor", "")
            p_words = _doc_words(p_doc)
            if not p_words:
                continue
            for a_idx, a_row in actual_df.iterrows():
                if a_idx in used_actual:
                    continue
                a_doc = a_row.get("Doctor", "")
                a_words = _doc_words(a_doc)
                if not a_words:
                    continue
                if p_words == a_words:
                    score = 200
                elif p_words.issubset(a_words) or a_words.issubset(p_words):
                    score = 150
                else:
                    score = fuzz.token_sort_ratio(_norm_doc(p_doc), _norm_doc(a_doc))
                    if score < FUZZY_DOC_THRESHOLD:
                        continue
                if not _corroborated(p_row, a_row):
                    continue
                candidates.append((score, p_idx, a_idx))

    candidates.sort(key=lambda c: c[0], reverse=True)
    for _, p_idx, a_idx in candidates:
        if p_idx in plan_to_actual or a_idx in used_actual:
            continue
        used_actual.add(a_idx)
        plan_to_actual[p_idx] = a_idx

    for p_idx, p_row in plan_df.iterrows():
        best = plan_to_actual.get(p_idx)

        if best is not None:
            a_row = actual_df.loc[best]
            used_actual.add(best)
            actual_ugx  = safe_num(a_row.get("Amount_UGX", 0))
            planned_ugx = safe_num(p_row.get("Amount_UGX", 0))
            planned_eur = safe_num(p_row.get("Amount_EUR", 0))
            matched.append({
                "doctor": p_row.get("Doctor", ""), "hospital": p_row.get("Hospital", ""),
                "speciality": p_row.get("Speciality", ""),
                "delegate": mr_display_name(p_row.get("Delegate", "")),
                "area": p_row.get("Area", ""), "activity": p_row.get("Activity", ""),
                "activity_id": a_row.get("Activity_ID", ""),
                "focus_products": p_row.get("Focus_Products", ""),
                "planned_ugx": planned_ugx, "planned_eur": planned_eur,
                "actual_ugx": actual_ugx,
                "actual_eur": safe_num(a_row.get("Amount_EUR", 0)),
                "variance_ugx": actual_ugx - planned_ugx,
                "sales_outcome": a_row.get("Sales_Outcome", []),
                "sales_outcome_eur": safe_num(a_row.get("Sales_Outcome_EUR", 0)),
                "has_outcome": bool(a_row.get("Sales_Outcome")),
                "num_visits": int(safe_num(a_row.get("Num_Visits", 0))),
                "responsible": a_row.get("Responsible", ""), "status": "executed",
            })
        else:
            planned_not_done.append({
                "doctor": p_row.get("Doctor", ""), "hospital": p_row.get("Hospital", ""),
                "speciality": p_row.get("Speciality", ""),
                "delegate": mr_display_name(p_row.get("Delegate", "")),
                "area": p_row.get("Area", ""), "activity": p_row.get("Activity", "VISIT"),
                "focus_products": p_row.get("Focus_Products", ""),
                "planned_ugx": safe_num(p_row.get("Amount_UGX", 0)),
                "planned_eur": safe_num(p_row.get("Amount_EUR", 0)),
                "actual_ugx": 0.0, "actual_eur": 0.0, "status": "planned_not_done",
            })

    if actual_df is not None and not actual_df.empty:
        for a_idx, a_row in actual_df.iterrows():
            if a_idx not in used_actual:
                unplanned_done.append({
                    "doctor": a_row.get("Doctor", ""), "hospital": a_row.get("Hospital", ""),
                    "speciality": a_row.get("Speciality", ""), "area": "",
                    "delegate": mr_display_name(a_row.get("MR_IDs", "").split(",")[0]) if a_row.get("MR_IDs") else "",
                    "activity": a_row.get("Activity", ""), "activity_id": a_row.get("Activity_ID", ""),
                    "focus_products": a_row.get("Products", ""),
                    "planned_ugx": 0.0, "actual_ugx": safe_num(a_row.get("Amount_UGX", 0)),
                    "actual_eur": safe_num(a_row.get("Amount_EUR", 0)),
                    "variance_ugx": safe_num(a_row.get("Amount_UGX", 0)),
                    "sales_outcome": a_row.get("Sales_Outcome", []),
                    "sales_outcome_eur": safe_num(a_row.get("Sales_Outcome_EUR", 0)),
                    "has_outcome": bool(a_row.get("Sales_Outcome")),
                    "num_visits": int(safe_num(a_row.get("Num_Visits", 0))),
                    "responsible": a_row.get("Responsible", ""), "status": "unplanned",
                })

    return matched, planned_not_done, unplanned_done


@router.get("/activities")
async def get_activities():
    cached = await get_api_cache("activities")
    if cached:
        return cached

    data = app_state.get("data", {})
    by_month: dict = {}
    overall = {
        "total_planned": 0, "executed": 0, "not_executed": 0, "unplanned": 0,
        "total_outcome_eur": 0.0,
        "planned_budget_ugx": 0.0, "planned_budget_eur": 0.0,
        "actual_spent_ugx": 0.0, "actual_spent_eur": 0.0,
        "with_outcome": 0, "without_outcome": 0,
    }

    for month_key, mdata in data.items():
        plan_df   = mdata.get("projection", {}).get("activity_plan")
        actual_df = mdata.get("expense", {}).get("activity_exp")
        other_df  = mdata.get("expense", {}).get("other_exp")
        matched, planned_not_done, unplanned = _match_activities(plan_df, actual_df)

        total_planned    = len(matched) + len(planned_not_done)
        executed_count   = len(matched)
        outcome_eur      = sum(r.get("sales_outcome_eur", 0) for r in matched)
        planned_budget   = sum(r.get("planned_ugx", 0) for r in matched) + sum(r.get("planned_ugx", 0) for r in planned_not_done)
        planned_budget_e = sum(r.get("planned_eur", 0) for r in matched) + sum(r.get("planned_eur", 0) for r in planned_not_done)
        other_spent      = safe_num(other_df["Amount_UGX"].sum()) if other_df is not None and not other_df.empty and "Amount_UGX" in other_df.columns else 0.0
        other_spent_eur  = safe_num(other_df["Amount_EUR"].sum()) if other_df is not None and not other_df.empty and "Amount_EUR" in other_df.columns else 0.0
        actual_spent     = sum(r.get("actual_ugx", 0) for r in matched) + sum(r.get("actual_ugx", 0) for r in unplanned) + other_spent
        actual_spent_eur = sum(r.get("actual_eur", 0) for r in matched) + sum(r.get("actual_eur", 0) for r in unplanned) + other_spent_eur
        with_outcome     = sum(1 for r in matched if r.get("has_outcome"))
        total_visits     = sum(r.get("num_visits", 0) for r in matched) + sum(r.get("num_visits", 0) for r in unplanned)

        by_month[month_key] = {
            "label": MONTH_LABELS.get(month_key, month_key.title()),
            "matched": matched, "planned_not_done": planned_not_done, "unplanned_done": unplanned,
            "summary": {
                "total_planned": total_planned, "executed": executed_count,
                "not_executed": len(planned_not_done), "unplanned": len(unplanned),
                "execution_rate_pct": (executed_count / total_planned * 100) if total_planned else 0.0,
                "planned_budget_ugx": planned_budget, "planned_budget_eur": planned_budget_e,
                "actual_spent_ugx": actual_spent, "actual_spent_eur": actual_spent_eur,
                "total_outcome_eur": outcome_eur, "with_outcome": with_outcome,
                "without_outcome": executed_count - with_outcome,
                "cost_per_visit_eur":    round(actual_spent_eur / total_visits, 2) if total_visits else None,
                "cost_per_outcome_eur":  round(actual_spent_eur / with_outcome, 2) if with_outcome else None,
                "roi_pct":               round(outcome_eur / actual_spent_eur * 100, 1) if actual_spent_eur else None,
            },
        }

        overall["total_planned"]       += total_planned
        overall["executed"]            += executed_count
        overall["not_executed"]        += len(planned_not_done)
        overall["unplanned"]           += len(unplanned)
        overall["total_outcome_eur"]   += outcome_eur
        overall["planned_budget_ugx"]  += planned_budget
        overall["planned_budget_eur"]  += planned_budget_e
        overall["actual_spent_ugx"]    += actual_spent
        overall["actual_spent_eur"]    += actual_spent_eur
        overall["with_outcome"]        += with_outcome
        overall["without_outcome"]     += executed_count - with_outcome

    overall["execution_rate_pct"] = (overall["executed"] / overall["total_planned"] * 100) if overall["total_planned"] else 0.0
    overall_spent_eur = overall["actual_spent_eur"]
    overall_visits    = sum(
        r.get("num_visits", 0)
        for mdata in by_month.values()
        for r in (mdata["matched"] + mdata["unplanned_done"])
    )
    overall["cost_per_visit_eur"]   = round(overall_spent_eur / overall_visits, 2) if overall_visits else None
    overall["cost_per_outcome_eur"] = round(overall_spent_eur / overall["with_outcome"], 2) if overall["with_outcome"] else None
    overall["roi_pct"]              = round(overall["total_outcome_eur"] / overall_spent_eur * 100, 1) if overall_spent_eur else None

    result = {"months": list(by_month.keys()), "by_month": by_month, "overall": overall, "activity_breakdown": {}}
    await set_api_cache("activities", result)
    return result
