"""
Data loaders for Uganda Pharma Dashboard.
Uganda sales file structure differs from IVC:
  - No distributor columns; single quantity (Unit) per product
  - All products are TABLET category
  - Currency: EUR already in sales/projection; UGX in budget fields
"""

import io
import os
import re
from pathlib import Path

import pandas as pd

from constants import UGX_TO_EUR, DISTRIBUTORS, ugx_to_eur, usd_to_eur
from name_map import (
    normalize_mr, mr_display_name,
    normalize_product, product_display_name, product_category, parse_multi_products,
    normalize_activity, activity_display_name,
    normalize_territory,
    normalize_doctor,
)
from utils import safe_num, _parse_header, col, read_col


# ── Month folder discovery ────────────────────────────────────────────────────

MONTH_FOLDER_MAP = {
    "january": "jan", "february": "feb", "march": "mar", "april": "apr",
    "may": "may", "june": "jun", "july": "jul", "august": "aug",
    "september": "sep", "october": "oct", "november": "nov", "december": "dec",
}


_MONTH_ORDER = list(MONTH_FOLDER_MAP.values())


def _discover_month_folders(storage) -> list[tuple[str, str]]:
    results = []
    try:
        for name in storage.list_dirs():
            key = MONTH_FOLDER_MAP.get(name.lower())
            if key:
                results.append((key, name))
    except Exception as e:
        print(f"[loaders] Month discovery error: {e}")
    results.sort(key=lambda kv: _MONTH_ORDER.index(kv[0]))
    return results


def _find_root_file(storage, kind: str) -> bytes | None:
    """Find master file in UGANDA root. kind: 'sales'"""
    try:
        for fname in storage.list_files(""):
            if fname.startswith("~$"):
                continue
            name_lower = fname.lower()
            if kind == "sales" and ("sale" in name_lower):
                return storage.get_file_bytes(fname)
    except Exception as e:
        print(f"[loaders] Root file search error for {kind!r}: {e}")
    return None


def _find_month_file(storage, folder: str, kind: str) -> bytes | None:
    kind_patterns = {
        "sale":       ["sale", "sales"],
        "projection": ["projection", "proj"],
        "expense":    ["expense", "exp"],
        "monthly":    ["monthly", "report"],
        "visit":      ["visit", "tracker"],
        "tour":       ["tour", "plan"],
    }
    patterns = kind_patterns.get(kind, [kind])
    try:
        for fname in storage.list_files(folder):
            if fname.startswith("~$"):
                continue
            fname_lower = fname.lower()
            if any(p in fname_lower for p in patterns):
                return storage.get_file_bytes(f"{folder}/{fname}")
    except Exception as e:
        print(f"[loaders] Month file search error ({kind} in {folder}): {e}")
    return None


# ── Canonical rate cache ──────────────────────────────────────────────────────

_canonical_rates: dict[str, float] = {}


def build_canonical_rates(sales_bytes: bytes):
    """Extract product → rate_eur from the master sales file."""
    global _canonical_rates
    try:
        xl = pd.ExcelFile(io.BytesIO(sales_bytes))
        df = xl.parse(xl.sheet_names[0], header=None)

        hdr_row = None
        for i, row in df.iterrows():
            vals = [str(v).lower() for v in row if pd.notna(v)]
            if any("product" in v for v in vals):
                hdr_row = i
                break
        if hdr_row is None:
            return

        hdr = _parse_header(df.iloc[hdr_row])
        product_col = col(hdr, "product")
        rate_col    = col(hdr, "price €", "price (eur)", "rate (eur)", "rate\n(eur)", "rate eur", "rate", "price")

        for _, row in df.iloc[hdr_row + 1:].iterrows():
            if product_col is None:
                break
            prod_raw = row.iloc[product_col]
            if pd.isna(prod_raw):
                continue
            prod_id = normalize_product(str(prod_raw).strip().upper())
            if rate_col is not None:
                rate = safe_num(row.iloc[rate_col])
                if rate > 0:
                    _canonical_rates[prod_id] = rate
    except Exception as e:
        print(f"[loaders] build_canonical_rates error: {e}")


# ── Sales loader ──────────────────────────────────────────────────────────────

def load_sales(file_bytes: bytes, tab_name: str | None = None) -> dict:
    """
    Load Uganda monthly sales tab.
    Uganda columns: Category, Product, Price €, Closing stock, Unit, Value(EURO)
    No distributor columns — Unit is total quantity sold.
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheet = tab_name if tab_name and tab_name in xl.sheet_names else xl.sheet_names[0]
        raw = xl.parse(sheet, header=None)

        hdr_row = 0
        for i, row in raw.iterrows():
            vals = [str(v).lower() for v in row if pd.notna(v)]
            if any("product" in v for v in vals):
                hdr_row = i
                break

        hdr = _parse_header(raw.iloc[hdr_row])

        rows = []
        current_category = "TABLET"
        for _, row in raw.iloc[hdr_row + 1:].iterrows():
            prod_idx   = col(hdr, "product")
            cat_idx    = col(hdr, "category")
            rate_idx   = col(hdr, "price €", "price (eur)", "rate (eur)", "rate eur", "rate", "price")
            unit_idx   = col(hdr, "unit", "units", "qty", "quantity", "sales")
            val_idx    = col(hdr, "value(euro)", "value (euro)", "value(eur)", "value (eur)", "value")
            close_idx  = col(hdr, "closing stock", "closing", "stock")

            if cat_idx is not None and pd.notna(row.iloc[cat_idx]):
                current_category = str(row.iloc[cat_idx]).strip().upper()

            prod_raw = row.iloc[prod_idx] if prod_idx is not None else None
            if pd.isna(prod_raw):
                continue

            prod_id  = normalize_product(str(prod_raw).strip().upper())
            rate     = _canonical_rates.get(prod_id, safe_num(row.iloc[rate_idx] if rate_idx is not None else 0))
            category = product_category(prod_id) or current_category
            units    = safe_num(row.iloc[unit_idx] if unit_idx is not None else None)
            val_eur  = safe_num(row.iloc[val_idx]  if val_idx  is not None else None)
            closing  = safe_num(row.iloc[close_idx] if close_idx is not None else None)

            # Use computed value if explicit value is missing
            if val_eur == 0 and units > 0 and rate > 0:
                val_eur = units * rate

            entry = {
                "Product":         product_display_name(prod_id),
                "Category":        category,
                "RATE":            rate,
                "TOTAL_SALES":     units,
                "TOTAL_VALUE_EUR": val_eur,
                "CLOSING_STOCK":   closing,
            }
            rows.append(entry)

        df_current = pd.DataFrame(rows)
        return {"current": df_current, "prev": pd.DataFrame()}

    except Exception as e:
        print(f"[loaders] load_sales error: {e}")
        return {"current": pd.DataFrame(), "prev": pd.DataFrame()}


# ── Projection loader ─────────────────────────────────────────────────────────

def load_projection(file_bytes: bytes) -> dict:
    """
    Load projection file.
    Uganda tabs: 'projection ' (trailing space), 'Activity plan'
    Projection columns: S.No, Product, Category, Price €, Target Units, Target Value (EUR)
    Activity plan columns: S.No, Doctor / Contact, Hospital / Clinic, Speciality,
                           MR NAME, Area, Amount (USD), Focus Products, Category
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheets_lower = {s.lower().strip(): s for s in xl.sheet_names}

        proj_sheet = (
            sheets_lower.get("projection") or
            sheets_lower.get("proj") or
            xl.sheet_names[0]
        )
        raw_proj = xl.parse(proj_sheet, header=None)

        hdr_row = 0
        for i, row in raw_proj.iterrows():
            vals = [str(v).lower() for v in row if pd.notna(v)]
            if any("product" in v for v in vals):
                hdr_row = i
                break

        hdr = _parse_header(raw_proj.iloc[hdr_row])
        proj_rows = []
        for _, row in raw_proj.iloc[hdr_row + 1:].iterrows():
            sno_idx   = col(hdr, "s.no", "s no", "sno", "no")
            prod_idx  = col(hdr, "product")
            cat_idx   = col(hdr, "category")
            rate_idx  = col(hdr, "price €", "price (eur)", "rate (eur)", "rate eur", "rate", "price")
            tgt_u_idx = col(hdr, "target units", "target\nunits")
            tgt_v_idx = col(hdr, "target value (eur)", "target value\n(eur)", "target value eur", "target value")

            sno_val = row.iloc[sno_idx] if sno_idx is not None else None
            try:
                sno_int = int(float(str(sno_val))) if pd.notna(sno_val) else None
            except (ValueError, TypeError):
                sno_int = None
            if sno_int is None or sno_int > 50:
                continue

            prod_raw = row.iloc[prod_idx] if prod_idx is not None else None
            if pd.isna(prod_raw):
                continue

            prod_id   = normalize_product(str(prod_raw).strip().upper())
            rate      = _canonical_rates.get(prod_id, safe_num(row.iloc[rate_idx] if rate_idx is not None else 0))
            tgt_units = safe_num(row.iloc[tgt_u_idx] if tgt_u_idx is not None else None)
            tgt_val   = safe_num(row.iloc[tgt_v_idx]) if tgt_v_idx is not None and pd.notna(row.iloc[tgt_v_idx]) else tgt_units * rate

            proj_rows.append({
                "Product":          product_display_name(prod_id),
                "Category":         product_category(prod_id) or (str(row.iloc[cat_idx]).strip().upper() if cat_idx is not None and pd.notna(row.iloc[cat_idx]) else ""),
                "RATE":             rate,
                "Target_Units":     tgt_units,
                "Target_Value_EUR": tgt_val,
            })

        df_proj = pd.DataFrame(proj_rows)

        act_sheet = (
            sheets_lower.get("activity plan") or
            sheets_lower.get("activity") or
            sheets_lower.get("plan")
        )
        df_act = pd.DataFrame()
        if act_sheet:
            raw_act = xl.parse(act_sheet, header=None)
            hdr_row_a = 0
            for i, row in raw_act.iterrows():
                vals = [str(v).lower() for v in row if pd.notna(v)]
                if any("doctor" in v or "delegate" in v or "mr" in v for v in vals):
                    hdr_row_a = i
                    break

            hdr_a = _parse_header(raw_act.iloc[hdr_row_a])
            act_rows = []
            for _, row in raw_act.iloc[hdr_row_a + 1:].iterrows():
                doc_idx  = col(hdr_a, "doctor / contact", "doctor/contact", "doctor", "contact")
                del_idx  = col(hdr_a, "mr name", "delegate", "mr", "responsible")
                hosp_idx = col(hdr_a, "hospital / clinic", "hospital/clinic", "hospital", "clinic")
                spec_idx = col(hdr_a, "speciality", "specialty")
                area_idx = col(hdr_a, "area", "territory", "zone")
                act_idx  = col(hdr_a, "activity type", "activity")
                amt_idx  = col(hdr_a, "amount (usd)", "amount (ugx)", "amount(ugx)", "amount (fcfa)", "amount")
                fp_idx   = col(hdr_a, "focus products", "focus product", "products")
                cat_idx  = col(hdr_a, "category")
                sno_idx  = col(hdr_a, "s.no", "s no", "sno", "no")

                doc_raw = row.iloc[doc_idx] if doc_idx is not None else None
                if pd.isna(doc_raw):
                    continue

                sno_val = row.iloc[sno_idx] if sno_idx is not None else None
                try:
                    sn = int(float(str(sno_val))) if pd.notna(sno_val) else 0
                except (ValueError, TypeError):
                    sn = 0
                if sn == 0:
                    continue

                del_raw  = row.iloc[del_idx] if del_idx is not None else None
                act_raw  = row.iloc[act_idx] if act_idx is not None else None
                area_raw = row.iloc[area_idx] if area_idx is not None else None
                fp_raw   = row.iloc[fp_idx] if fp_idx is not None else None

                amt_usd_plan = safe_num(row.iloc[amt_idx] if amt_idx is not None else None)
                amt_eur_plan = usd_to_eur(amt_usd_plan)
                act_rows.append({
                    "SN":           sn,
                    "Doctor":       normalize_doctor(str(doc_raw).strip()) if pd.notna(doc_raw) else "",
                    "Hospital":     str(row.iloc[hosp_idx]).strip() if hosp_idx is not None and pd.notna(row.iloc[hosp_idx]) else "",
                    "Speciality":   str(row.iloc[spec_idx]).strip() if spec_idx is not None and pd.notna(row.iloc[spec_idx]) else "",
                    "Delegate":     normalize_mr(str(del_raw).strip().upper()) if pd.notna(del_raw) else "",
                    "Area":         str(area_raw).strip() if pd.notna(area_raw) else "",
                    "Activity":     activity_display_name(normalize_activity(str(act_raw).strip().upper())) if act_raw is not None and pd.notna(act_raw) else "VISIT",
                    "Amount_EUR":   amt_eur_plan,
                    "Amount_UGX":   amt_eur_plan * UGX_TO_EUR,
                    "Focus_Products": parse_multi_products(str(fp_raw)) if fp_raw is not None and pd.notna(fp_raw) else "",
                    "Category":     str(row.iloc[cat_idx]).strip().upper() if cat_idx is not None and pd.notna(row.iloc[cat_idx]) else "",
                })

            df_act = pd.DataFrame(act_rows)

        return {
            "projection":    df_proj,
            "activity_plan": df_act,
            "missing_sheets": [],
        }

    except Exception as e:
        print(f"[loaders] load_projection error: {e}")
        return {"projection": pd.DataFrame(), "activity_plan": pd.DataFrame(), "missing_sheets": [str(e)]}


# ── Expense loader ────────────────────────────────────────────────────────────

def load_expense(file_bytes: bytes) -> dict:
    """
    Load expense file.
    Uganda tabs: 'MONEY REVEIVED' (typo in source), 'ACTIVITY EXPENSES', 'Other EXP'
    Note: Activity Expenses 'Amount (UGX)' column actually contains USD values.
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheets_lower = {s.lower().strip(): s for s in xl.sheet_names}
        missing = []

        # ── Money Received ──
        mr_sheet = (
            sheets_lower.get("money reveived") or   # Uganda typo
            sheets_lower.get("money received") or
            sheets_lower.get("money") or
            sheets_lower.get("budget")
        )
        opening_balance_eur = new_budget_eur = total_spent_eur = balance_eur = 0.0
        df_mr = pd.DataFrame()

        if mr_sheet:
            raw_mr = xl.parse(mr_sheet, header=None)
            hdr_row = 0
            for i, row in raw_mr.iterrows():
                vals = [str(v).lower() for v in row if pd.notna(v)]
                if any("type" in v or "amount" in v for v in vals):
                    hdr_row = i
                    break
            hdr = _parse_header(raw_mr.iloc[hdr_row])
            type_idx    = col(hdr, "type")
            amt_ugx_idx = col(hdr, "amount (ugx)", "amount(ugx)")
            amt_usd_idx = col(hdr, "amount (usd)", "amount(usd)")
            if amt_ugx_idx is None and amt_usd_idx is None:
                amt_ugx_idx = col(hdr, "amount")
            date_idx    = col(hdr, "date")
            src_idx     = col(hdr, "source / description", "description", "source")
            notes_idx   = col(hdr, "notes", "remarks")

            mr_rows = []
            for _, row in raw_mr.iloc[hdr_row + 1:].iterrows():
                type_raw = row.iloc[type_idx] if type_idx is not None else None
                ugx_raw  = row.iloc[amt_ugx_idx] if amt_ugx_idx is not None else None
                usd_raw  = row.iloc[amt_usd_idx] if amt_usd_idx is not None else None
                if pd.isna(type_raw) and pd.isna(ugx_raw) and pd.isna(usd_raw):
                    continue

                type_str  = str(type_raw).strip().upper() if pd.notna(type_raw) else ""
                ugx_amt   = safe_num(ugx_raw)
                usd_amt   = safe_num(usd_raw)
                # Both columns often represent the same amount in different currencies —
                # prefer USD; fall back to UGX only if USD is absent.
                row_eur   = usd_to_eur(usd_amt) if usd_amt else ugx_to_eur(ugx_amt)

                type_lower = type_str.lower()
                if "opening" in type_lower:
                    opening_balance_eur = row_eur
                elif "received" in type_lower:
                    new_budget_eur += row_eur
                elif "spent" in type_lower:
                    total_spent_eur += row_eur
                elif "balance" in type_lower:
                    balance_eur = row_eur

                date_val  = row.iloc[date_idx]  if date_idx  is not None else None
                src_val   = row.iloc[src_idx]   if src_idx   is not None else None
                notes_val = row.iloc[notes_idx] if notes_idx is not None else None

                mr_rows.append({
                    "Type":       type_str,
                    "Date":       pd.to_datetime(date_val, errors="coerce") if pd.notna(date_val) else None,
                    "Source":     str(src_val).strip()   if pd.notna(src_val)   else "",
                    "Amount_UGX": ugx_amt,
                    "Amount_USD": usd_amt,
                    "Amount_EUR": row_eur,
                    "Notes":      str(notes_val).strip() if pd.notna(notes_val) else "",
                })
            df_mr = pd.DataFrame(mr_rows)
        else:
            missing.append("MONEY RECEIVED")

        total_received_eur = opening_balance_eur + new_budget_eur

        # ── Activity Expenses ──
        ae_sheet = (
            sheets_lower.get("activity expenses") or
            sheets_lower.get("activity exp.") or
            sheets_lower.get("activities")
        )
        df_ae = pd.DataFrame()
        if ae_sheet:
            raw_ae = xl.parse(ae_sheet, header=None)
            hdr_row_ae = 0
            for i, row in raw_ae.iterrows():
                vals = [str(v).lower() for v in row if pd.notna(v)]
                if any("doctor" in v or "hospital" in v for v in vals):
                    hdr_row_ae = i
                    break

            hdr_ae   = _parse_header(raw_ae.iloc[hdr_row_ae])
            sno_idx  = col(hdr_ae, "s.no", "s no", "sno", "no")
            doc_idx  = col(hdr_ae, "doctor name", "doctor / contact", "doctor/contact", "doctor", "contact")
            hosp_idx = col(hdr_ae, "hospital / pharmacy name", "hospital / pharmacy", "hospital / clinic", "hospital/clinic", "hospital", "pharmacy")
            spec_idx = col(hdr_ae, "speciality", "specialty")
            act_idx  = col(hdr_ae, "activity type", "activity")
            prod_idx = col(hdr_ae, "products", "focus products", "product")
            amt_idx  = col(hdr_ae, "amount (ugx)", "amount(ugx)", "amount (usd)", "amount")
            resp_idx = col(hdr_ae, "responsible", "delegate", "mr", "responsible mr")
            out_idx  = col(hdr_ae, "sales outcome", "outcome")
            vis_idx  = col(hdr_ae, "no. of visits", "no of visits", "visits")
            cont_idx = col(hdr_ae, "contact number", "contact")

            ae_rows = []
            for _, row in raw_ae.iloc[hdr_row_ae + 1:].iterrows():
                doc_raw = row.iloc[doc_idx] if doc_idx is not None else None
                if pd.isna(doc_raw):
                    continue

                act_raw  = row.iloc[act_idx]  if act_idx  is not None else None
                resp_raw = row.iloc[resp_idx] if resp_idx is not None else None
                amt_usd  = safe_num(row.iloc[amt_idx] if amt_idx is not None else None)
                amt_eur  = usd_to_eur(amt_usd)
                amt_ugx  = amt_eur * UGX_TO_EUR
                prod_raw = row.iloc[prod_idx] if prod_idx is not None else None
                out_raw  = row.iloc[out_idx]  if out_idx  is not None else None
                vis_raw  = row.iloc[vis_idx]  if vis_idx  is not None else None

                sales_outcome = ""
                outcome_eur = 0.0
                if pd.notna(out_raw) and str(out_raw).strip() and str(out_raw).strip() not in ("0", "nan"):
                    sales_outcome = str(out_raw).strip()
                    try:
                        total_units = int(float(sales_outcome))
                        if total_units > 0:
                            outcome_eur = total_units * amt_usd / max(total_units, 1) * 0.5 if total_units else 0
                    except (ValueError, TypeError):
                        pass

                resp_str = str(resp_raw).strip().upper() if pd.notna(resp_raw) else ""
                mr_id    = normalize_mr(resp_str)
                mr_ids   = [mr_id] if mr_id else []
                num_mrs  = max(len(mr_ids), 1)

                try:
                    sn = int(float(str(row.iloc[sno_idx]))) if sno_idx is not None and pd.notna(row.iloc[sno_idx]) else 0
                except (ValueError, TypeError):
                    sn = 0

                ae_rows.append({
                    "SN":               sn,
                    "Doctor":           normalize_doctor(str(doc_raw).strip()),
                    "Hospital":         str(row.iloc[hosp_idx]).strip() if hosp_idx is not None and pd.notna(row.iloc[hosp_idx]) else "",
                    "Speciality":       str(row.iloc[spec_idx]).strip() if spec_idx is not None and pd.notna(row.iloc[spec_idx]) else "",
                    "Activity":         activity_display_name(normalize_activity(str(act_raw).strip().upper())) if act_raw is not None and pd.notna(act_raw) else "VISIT",
                    "Activity_ID":      normalize_activity(str(act_raw).strip().upper()) if act_raw is not None and pd.notna(act_raw) else "VISIT",
                    "Products":         parse_multi_products(str(prod_raw)) if prod_raw is not None and pd.notna(prod_raw) else "",
                    "Amount_UGX":       amt_ugx,
                    "Amount_EUR":       amt_eur,
                    "Amount_UGX_Share": amt_ugx / num_mrs,
                    "Contact":          str(row.iloc[cont_idx]).strip() if cont_idx is not None and pd.notna(row.iloc[cont_idx]) else "",
                    "Responsible":      resp_str,
                    "MR_IDs":           ",".join(mr_ids),
                    "Num_MRs":          num_mrs,
                    "Sales_Outcome":    sales_outcome,
                    "Sales_Outcome_EUR": outcome_eur,
                    "Num_Visits":       int(safe_num(vis_raw)) if vis_raw is not None and pd.notna(vis_raw) else 0,
                })
            df_ae = pd.DataFrame(ae_rows)
        else:
            missing.append("ACTIVITY EXPENSES")

        # ── Other Expenses ──
        oe_sheet = (
            sheets_lower.get("other exp") or
            sheets_lower.get("other expenses") or
            sheets_lower.get("other exp.")
        )
        df_oe = pd.DataFrame()
        if oe_sheet:
            raw_oe = xl.parse(oe_sheet, header=None)
            hdr_row_oe = 0
            for i, row in raw_oe.iterrows():
                vals = [str(v).lower() for v in row if pd.notna(v)]
                if any("detail" in v or "amount" in v or "country" in v for v in vals):
                    hdr_row_oe = i
                    break

            hdr_oe  = _parse_header(raw_oe.iloc[hdr_row_oe])
            oe_rows = []
            for _, row in raw_oe.iloc[hdr_row_oe + 1:].iterrows():
                det_idx = col(hdr_oe, "details", "description")
                amt_idx = col(hdr_oe, "amount (ugx)", "amount(ugx)", "amount (usd)", "amount")
                cmt_idx = col(hdr_oe, "comments", "notes", "remarks")
                cat_idx = col(hdr_oe, "category")
                cty_idx = col(hdr_oe, "country")
                sno_idx = col(hdr_oe, "s.no", "s no", "sno", "no")

                det_raw = row.iloc[det_idx] if det_idx is not None else None
                amt_raw = row.iloc[amt_idx] if amt_idx is not None else None
                if pd.isna(det_raw) and pd.isna(amt_raw):
                    continue

                try:
                    sn = int(float(str(row.iloc[sno_idx]))) if sno_idx is not None and pd.notna(row.iloc[sno_idx]) else 0
                except (ValueError, TypeError):
                    sn = 0

                amt_usd = safe_num(amt_raw)
                oe_rows.append({
                    "SN":         sn,
                    "Country":    str(row.iloc[cty_idx]).strip() if cty_idx is not None and pd.notna(row.iloc[cty_idx]) else "",
                    "Details":    str(det_raw).strip() if pd.notna(det_raw) else "",
                    "Amount_UGX": amt_usd * UGX_TO_EUR,
                    "Amount_EUR": amt_usd,
                    "Comments":   str(row.iloc[cmt_idx]).strip() if cmt_idx is not None and pd.notna(row.iloc[cmt_idx]) else "",
                    "Category":   str(row.iloc[cat_idx]).strip().upper() if cat_idx is not None and pd.notna(row.iloc[cat_idx]) else "",
                })
            df_oe = pd.DataFrame(oe_rows)
        else:
            missing.append("OTHER EXPENSES")

        return {
            "activity_exp":        df_ae,
            "other_exp":           df_oe,
            "money_received":      df_mr,
            "opening_balance_ugx": opening_balance_eur * UGX_TO_EUR,
            "new_budget_ugx":      new_budget_eur      * UGX_TO_EUR,
            "total_received_ugx":  total_received_eur  * UGX_TO_EUR,
            "total_spent_ugx":     total_spent_eur     * UGX_TO_EUR,
            "balance_ugx":         balance_eur         * UGX_TO_EUR,
            "opening_balance_eur": opening_balance_eur,
            "new_budget_eur":      new_budget_eur,
            "total_received_eur":  total_received_eur,
            "total_spent_eur":     total_spent_eur,
            "balance_eur":         balance_eur,
            "missing_sheets":      missing,
        }

    except Exception as e:
        print(f"[loaders] load_expense error: {e}")
        return {
            "activity_exp": pd.DataFrame(), "other_exp": pd.DataFrame(),
            "money_received": pd.DataFrame(),
            "opening_balance_ugx": 0.0, "new_budget_ugx": 0.0,
            "total_received_ugx": 0.0,  "total_spent_ugx": 0.0, "balance_ugx": 0.0,
            "opening_balance_eur": 0.0, "new_budget_eur": 0.0,
            "total_received_eur": 0.0,  "total_spent_eur": 0.0, "balance_eur": 0.0,
            "missing_sheets": [str(e)],
        }


# ── Monthly Reports loader ────────────────────────────────────────────────────

def load_monthly_reports(file_bytes: bytes) -> dict:
    """
    Load monthly reports file.
    Uganda tabs: DELEGATES, BUDGET ANALYSIS
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheets_lower = {s.lower(): s for s in xl.sheet_names}
        missing = []

        del_sheet = (
            sheets_lower.get("delegates") or
            sheets_lower.get("delegate") or
            sheets_lower.get("mr performance") or
            xl.sheet_names[0]
        )
        raw_del = xl.parse(del_sheet, header=None)

        hdr_row = 0
        for i, row in raw_del.iterrows():
            non_null = [str(v).lower() for v in row if pd.notna(v)]
            # Must have multiple columns and a "delegate name" or similar multi-word key
            if len(non_null) >= 3 and any("delegate name" in v or ("delegate" in v and "name" in v) or "s.no" in v for v in non_null):
                hdr_row = i
                break

        hdr = _parse_header(raw_del.iloc[hdr_row])
        del_rows = []
        for _, row in raw_del.iloc[hdr_row + 1:].iterrows():
            sno_idx  = col(hdr, "s.no", "s no", "sno", "no")
            name_idx = col(hdr, "delegate name", "name", "delegate")
            terr_idx = col(hdr, "territory", "area", "zone", "region")
            np_idx   = col(hdr, "non prescriber\ncalls", "non prescriber calls", "non prescriber")
            pc_idx   = col(hdr, "prescriber\ncalls", "prescriber calls", "prescriber")
            dc_idx   = col(hdr, "drs\nconverted", "drs converted", "converted")
            tc_idx   = col(hdr, "total calls", "calls")
            ph_idx   = col(hdr, "pharmacy\ncalls", "pharmacy calls", "pharmacy")
            dt_idx   = col(hdr, "days\ntarget", "days target")
            dw_idx   = col(hdr, "days\nworked", "days worked")
            acd_idx  = col(hdr, "avg calls\nper day", "avg calls per day", "avg calls")
            ord_idx  = col(hdr, "total orders\n(eur)", "total orders (eur)", "total orders")
            ctc_idx  = col(hdr, "ctc\n(usd)", "ctc\n(eur)", "ctc (eur)", "ctc (usd)", "ctc")
            dil_idx  = col(hdr, "dr in list", "dr list")
            ldc_idx  = col(hdr, "listed dr covered", "listed covered")
            pdc_idx  = col(hdr, "% dr covered as per list", "% dr covered", "pct covered")

            name_raw = row.iloc[name_idx] if name_idx is not None else None
            if pd.isna(name_raw):
                continue

            try:
                sn = int(float(str(row.iloc[sno_idx]))) if sno_idx is not None and pd.notna(row.iloc[sno_idx]) else 0
            except (ValueError, TypeError):
                sn = 0

            terr_raw = row.iloc[terr_idx] if terr_idx is not None else None

            pct_raw = row.iloc[pdc_idx] if pdc_idx is not None else None
            pct_dr = None
            if pd.notna(pct_raw):
                pct_str = str(pct_raw).replace("%", "").strip()
                try:
                    pct_val = float(pct_str)
                    pct_dr = pct_val / 100.0 if pct_val > 1.0 else pct_val
                except (ValueError, TypeError):
                    pct_dr = None

            del_rows.append({
                "SN":             sn,
                "Delegate":       normalize_mr(str(name_raw).strip().upper()),
                "Delegate_Raw":   str(name_raw).strip(),
                "Territory":      normalize_territory(str(terr_raw).strip().upper()) if pd.notna(terr_raw) else "",
                "NonPrescriber":  safe_num(row.iloc[np_idx]  if np_idx  is not None else None),
                "Prescriber":     safe_num(row.iloc[pc_idx]  if pc_idx  is not None else None),
                "DrsConverted":   safe_num(row.iloc[dc_idx]  if dc_idx  is not None else None),
                "TotalCalls":     safe_num(row.iloc[tc_idx]  if tc_idx  is not None else None),
                "PharmacyCalls":  safe_num(row.iloc[ph_idx]  if ph_idx  is not None else None),
                "DaysTarget":     safe_num(row.iloc[dt_idx]  if dt_idx  is not None else None),
                "DaysWorked":     safe_num(row.iloc[dw_idx]  if dw_idx  is not None else None),
                "AvgCallsPerDay": safe_num(row.iloc[acd_idx] if acd_idx is not None else None),
                "TotalOrders":    safe_num(row.iloc[ord_idx] if ord_idx is not None else None),
                "CTC":            usd_to_eur(safe_num(row.iloc[ctc_idx] if ctc_idx is not None else None)),
                "DrInList":       int(safe_num(row.iloc[dil_idx] if dil_idx is not None else None)) or None,
                "ListedDRCovered": int(safe_num(row.iloc[ldc_idx] if ldc_idx is not None else None)) or None,
                "PctDRCovered":   pct_dr,
            })

        df_del = pd.DataFrame(del_rows)

        ba_sheet = sheets_lower.get("budget analysis") or sheets_lower.get("budget")
        df_ba = pd.DataFrame()
        if ba_sheet:
            raw_ba = xl.parse(ba_sheet, header=None)
            hdr_row_ba = 0
            for i, row in raw_ba.iterrows():
                vals = [str(v).lower() for v in row if pd.notna(v)]
                if any("doctor" in v or "activity" in v or "responsible" in v for v in vals):
                    hdr_row_ba = i
                    break

            hdr_ba  = _parse_header(raw_ba.iloc[hdr_row_ba])
            ba_rows = []
            for _, row in raw_ba.iloc[hdr_row_ba + 1:].iterrows():
                doc_idx  = col(hdr_ba, "doctor / contact", "doctor/contact", "doctor")
                area_idx = col(hdr_ba, "area / hospital", "area/hospital", "area", "hospital")
                mr_idx   = col(hdr_ba, "responsible mr", "responsible", "mr", "delegate")
                act_idx  = col(hdr_ba, "activity type", "activity")
                amt_idx  = col(hdr_ba, "amount (ugx)", "amount(ugx)", "amount (fcfa)", "amount")

                doc_raw = row.iloc[doc_idx] if doc_idx is not None else None
                if pd.isna(doc_raw):
                    continue

                mr_raw  = row.iloc[mr_idx]  if mr_idx  is not None else None
                act_raw = row.iloc[act_idx] if act_idx is not None else None
                amt_ugx = safe_num(row.iloc[amt_idx] if amt_idx is not None else None)

                ba_rows.append({
                    "Doctor":       normalize_doctor(str(doc_raw).strip()),
                    "Area":         str(row.iloc[area_idx]).strip() if area_idx is not None and pd.notna(row.iloc[area_idx]) else "",
                    "MR":           normalize_mr(str(mr_raw).strip().upper()) if pd.notna(mr_raw) else "",
                    "ActivityType": activity_display_name(normalize_activity(str(act_raw).strip().upper())) if act_raw is not None and pd.notna(act_raw) else "",
                    "Value_UGX":    amt_ugx,
                })
            df_ba = pd.DataFrame(ba_rows)
        else:
            missing.append("BUDGET ANALYSIS")

        return {"delegates": df_del, "budget_analysis": df_ba, "missing_sheets": missing}

    except Exception as e:
        print(f"[loaders] load_monthly_reports error: {e}")
        return {"delegates": pd.DataFrame(), "budget_analysis": pd.DataFrame(), "missing_sheets": [str(e)]}


# ── Visit Tracker loader ──────────────────────────────────────────────────────

def load_visit_tracker(file_bytes: bytes, month_key: str) -> pd.DataFrame:
    """
    Load visit tracker file. Uganda: one sheet per MR (George, Aisha, Rachelle, Simon).
    Header row is at index 3 (row 4): S.No, Doctor Name, Speciality, Hospital/Clinic, Mobile, Visit 1…Visit 7
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        all_rows = []

        for sheet_name in xl.sheet_names:
            if sheet_name.lower() in ("summary", "index", "template", "instructions"):
                continue

            raw = xl.parse(sheet_name, header=None)
            if raw.empty or len(raw) < 5:
                continue

            # Row 1 (index 0): Name of MR, <actual name>
            # Row 4 (index 3): S.No, Doctor Name, Speciality, ...
            cell_name = None
            for r in range(min(3, len(raw))):
                for c_i in range(min(5, len(raw.columns))):
                    val = raw.iloc[r, c_i]
                    if pd.notna(val) and str(val).strip():
                        cell_val = str(val).strip().upper()
                        # Skip row-label cells like "NAME OF MR", "TERRITORY", "COUNTRY"
                        if cell_val in ("NAME OF MR", "TERRITORY", "COUNTRY", "S.NO"):
                            continue
                        if any(ch.isalpha() for ch in cell_val) and len(cell_val) > 3:
                            cell_name = cell_val
                            break
                if cell_name:
                    break

            mr_raw  = cell_name or sheet_name.strip().upper()
            mr_id   = normalize_mr(mr_raw)
            mr_disp = mr_display_name(mr_id)

            # Find header row (has "Doctor Name")
            hdr_row_v = 3
            for i in range(min(6, len(raw))):
                vals = [str(v).lower() for v in raw.iloc[i] if pd.notna(v)]
                if any("doctor" in v or "s.no" in v for v in vals):
                    hdr_row_v = i
                    break

            hdr = _parse_header(raw.iloc[hdr_row_v])
            doc_idx    = col(hdr, "doctor name", "doctor", "name")
            spec_idx   = col(hdr, "speciality", "specialty", "specialization")
            clin_idx   = col(hdr, "hospital/clinic", "hospital / clinic", "clinic", "hospital")
            listed_idx = col(hdr, "listed/non listed", "listed/unlisted", "listed / unlisted", "listed", "unlisted")

            # Visit date columns: "Visit 1" through "Visit 7"
            date_cols = []
            for key, idx in hdr.items():
                if re.match(r'visit\s*\d+', key) or re.match(r'\d{1,2}[/\-]\d{1,2}', key):
                    date_cols.append(idx)
                elif key.startswith("date") and "visit" in key:
                    date_cols.append(idx)

            for _, row in raw.iloc[hdr_row_v + 1:].iterrows():
                doc_raw = row.iloc[doc_idx] if doc_idx is not None else None
                if pd.isna(doc_raw):
                    continue
                # Skip rows where doc_raw is a number (S.No values in trailing rows)
                try:
                    float(str(doc_raw))
                    continue
                except (ValueError, TypeError):
                    pass

                spec = str(row.iloc[spec_idx]).strip() if spec_idx is not None and pd.notna(row.iloc[spec_idx]) else ""
                clin = str(row.iloc[clin_idx]).strip() if clin_idx is not None and pd.notna(row.iloc[clin_idx]) else ""
                doctor = normalize_doctor(str(doc_raw).strip())
                listed_raw = row.iloc[listed_idx] if listed_idx is not None and listed_idx < len(row) else None
                listed = str(listed_raw).strip().upper() if listed_idx is not None and pd.notna(listed_raw) else ""

                if date_cols:
                    has_visit = False
                    for dc in date_cols:
                        cell = row.iloc[dc] if dc < len(row) else None
                        if pd.notna(cell) and str(cell).strip() not in ("", "0", "nan"):
                            parsed_date = pd.to_datetime(cell, errors="coerce", dayfirst=True)
                            if pd.isna(parsed_date):
                                continue
                            has_visit = True
                            all_rows.append({
                                "MR_ID":      mr_id,
                                "MR":         mr_disp,
                                "Doctor":     doctor,
                                "Speciality": spec,
                                "Clinic":     clin,
                                "Listed":     listed,
                                "Visit_Date": parsed_date,
                                "Month":      month_key,
                            })
                    if not has_visit:
                        # Doctor listed but no visit dates — still add with null date to count unique doctors
                        all_rows.append({
                            "MR_ID":      mr_id,
                            "MR":         mr_disp,
                            "Doctor":     doctor,
                            "Speciality": spec,
                            "Clinic":     clin,
                            "Listed":     listed,
                            "Visit_Date": None,
                            "Month":      month_key,
                        })
                else:
                    all_rows.append({
                        "MR_ID":      mr_id,
                        "MR":         mr_disp,
                        "Doctor":     doctor,
                        "Speciality": spec,
                        "Clinic":     clin,
                        "Listed":     listed,
                        "Visit_Date": None,
                        "Month":      month_key,
                    })

        return pd.DataFrame(all_rows)

    except Exception as e:
        print(f"[loaders] load_visit_tracker error: {e}")
        return pd.DataFrame()


# ── Tour Plan loader ──────────────────────────────────────────────────────────

def _is_covered(planned: str, actual: str) -> bool:
    if not planned or not actual:
        return False
    p_words = set(re.split(r'\W+', planned.upper()))
    a_words = set(re.split(r'\W+', actual.upper()))
    p_words.discard("")
    a_words.discard("")
    # "MEETING" planned and "MEETING" actual → covered
    if "MEETING" in p_words and "MEETING" in a_words:
        return True
    return bool(p_words & a_words)


def load_tour_plan(file_bytes: bytes) -> pd.DataFrame:
    """
    Load tour plan file.
    Uganda: single sheet 'Sheet1'
    Columns: Date, MR Name, Joint Working, Tour Plan (Planned Area), Actual Working Area
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheets_lower = {s.lower(): s for s in xl.sheet_names}
        sheet = (
            sheets_lower.get("tour plan") or
            sheets_lower.get("tour") or
            sheets_lower.get("sheet1") or
            xl.sheet_names[0]
        )
        raw = xl.parse(sheet, header=None)

        hdr_row = 0
        for i, row in raw.iterrows():
            vals = [str(v).lower() for v in row if pd.notna(v)]
            if any("date" in v or "mr" in v or "name" in v for v in vals):
                hdr_row = i
                break

        hdr         = _parse_header(raw.iloc[hdr_row])
        date_idx    = col(hdr, "date")
        mr_idx      = col(hdr, "mr name", "name", "mr", "delegate")
        joint_idx   = col(hdr, "joint working", "joint")
        planned_idx = col(hdr, "tour plan (planned area)", "planned area", "tour plan", "planned")
        actual_idx  = col(hdr, "actual working area", "actual area", "working area", "actual")

        rows = []
        for _, row in raw.iloc[hdr_row + 1:].iterrows():
            date_raw = row.iloc[date_idx] if date_idx is not None else None
            if pd.isna(date_raw):
                continue
            parsed_date = pd.to_datetime(date_raw, errors="coerce", dayfirst=True)
            if pd.isna(parsed_date):
                continue

            mr_raw     = row.iloc[mr_idx]      if mr_idx      is not None else None
            joint_raw  = row.iloc[joint_idx]   if joint_idx   is not None else None
            plan_raw   = row.iloc[planned_idx] if planned_idx is not None else None
            actual_raw = row.iloc[actual_idx]  if actual_idx  is not None else None

            mr_str     = str(mr_raw).strip().upper()    if pd.notna(mr_raw)     else ""
            joint_str  = str(joint_raw).strip()         if pd.notna(joint_raw)  else ""
            plan_str   = str(plan_raw).strip()          if pd.notna(plan_raw)   else ""
            actual_str = str(actual_raw).strip()        if pd.notna(actual_raw) else ""

            rows.append({
                "Date":          parsed_date,
                "MR":            normalize_mr(mr_str),
                "MR_Raw":        mr_str,
                "Joint_Working": joint_str,
                "Planned_Area":  plan_str,
                "Actual_Area":   actual_str,
                "Covered":       _is_covered(plan_str, actual_str),
            })

        return pd.DataFrame(rows)

    except Exception as e:
        print(f"[loaders] load_tour_plan error: {e}")
        return pd.DataFrame()


# ── Annual Projections loader ─────────────────────────────────────────────────

def load_annual_projections(file_bytes: bytes) -> dict[str, float]:
    """
    For Uganda, annual projections come from the projection file (Target_Value_EUR).
    Returns {product_name: target_eur}.
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheets_lower = {s.lower().strip(): s for s in xl.sheet_names}

        proj_sheet = sheets_lower.get("projection") or xl.sheet_names[0]
        raw = xl.parse(proj_sheet, header=None)

        hdr_row = 0
        for i, row in raw.iterrows():
            vals = [str(v).lower() for v in row if pd.notna(v)]
            if any("product" in v for v in vals):
                hdr_row = i
                break

        hdr = _parse_header(raw.iloc[hdr_row])
        sno_idx = col(hdr, "s.no", "s no", "sno", "no")
        prod_idx = col(hdr, "product")
        tgt_v_idx = col(hdr, "target value (eur)", "target value\n(eur)", "target value eur", "target value")

        result = {}
        for _, row in raw.iloc[hdr_row + 1:].iterrows():
            sno_val = row.iloc[sno_idx] if sno_idx is not None else None
            try:
                sno_int = int(float(str(sno_val))) if pd.notna(sno_val) else None
            except (ValueError, TypeError):
                sno_int = None
            if sno_int is None or sno_int > 50:
                continue

            prod_raw = row.iloc[prod_idx] if prod_idx is not None else None
            if pd.isna(prod_raw):
                continue

            prod_id = normalize_product(str(prod_raw).strip().upper())
            tgt_val = safe_num(row.iloc[tgt_v_idx]) if tgt_v_idx is not None else 0.0
            if tgt_val > 0:
                result[product_display_name(prod_id)] = tgt_val

        return result

    except Exception as e:
        print(f"[loaders] load_annual_projections error: {e}")
        return {}


# ── Master loader ─────────────────────────────────────────────────────────────

def load_all_data(storage) -> dict:
    """Load all Uganda data files from local storage."""
    data = {}
    months = _discover_month_folders(storage)

    sales_bytes = _find_root_file(storage, "sales")
    if sales_bytes:
        build_canonical_rates(sales_bytes)

    for month_key, folder_name in months:
        print(f"[loaders] Loading {folder_name} ({month_key})...")
        month_data = {}

        month_sales_b = _find_month_file(storage, folder_name, "sale") or sales_bytes
        if month_sales_b:
            month_data["sales"] = load_sales(month_sales_b)
        else:
            month_data["sales"] = {"current": pd.DataFrame(), "prev": pd.DataFrame()}

        proj_b = _find_month_file(storage, folder_name, "projection")
        month_data["projection"] = load_projection(proj_b) if proj_b else {
            "projection": pd.DataFrame(), "activity_plan": pd.DataFrame(), "missing_sheets": ["not found"]
        }

        exp_b = _find_month_file(storage, folder_name, "expense")
        month_data["expense"] = load_expense(exp_b) if exp_b else {
            "activity_exp": pd.DataFrame(), "other_exp": pd.DataFrame(),
            "money_received": pd.DataFrame(),
            "opening_balance_ugx": 0.0, "new_budget_ugx": 0.0,
            "total_received_ugx": 0.0, "total_spent_ugx": 0.0, "balance_ugx": 0.0,
            "opening_balance_eur": 0.0, "new_budget_eur": 0.0,
            "total_received_eur": 0.0, "total_spent_eur": 0.0, "balance_eur": 0.0,
            "missing_sheets": ["not found"],
        }

        monthly_b = _find_month_file(storage, folder_name, "monthly")
        month_data["monthly"] = load_monthly_reports(monthly_b) if monthly_b else {
            "delegates": pd.DataFrame(), "budget_analysis": pd.DataFrame(), "missing_sheets": ["not found"]
        }

        tour_b = _find_month_file(storage, folder_name, "tour")
        month_data["tour"] = load_tour_plan(tour_b) if tour_b else pd.DataFrame()

        visit_b = _find_month_file(storage, folder_name, "visit")
        month_data["visits"] = load_visit_tracker(visit_b, month_key) if visit_b else pd.DataFrame()

        data[month_key] = month_data
        s_cnt = len(month_data["sales"]["current"]) if month_data["sales"]["current"] is not None else 0
        v_cnt = len(month_data["visits"]) if month_data["visits"] is not None and not month_data["visits"].empty else 0
        print(f"[loaders]   OK {month_key}: sales={s_cnt} products, visits={v_cnt}")

    return data
