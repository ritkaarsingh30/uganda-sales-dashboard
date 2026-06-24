import math
import pandas as pd


def safe_num(val, default=0.0):
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def _parse_header(row) -> dict[str, int]:
    result = {}
    for i, val in enumerate(row):
        if pd.isna(val):
            continue
        key = str(val).strip().lower().replace("\n", " ")
        key = " ".join(key.split())
        result[key] = i
    return result


def col(hdr: dict, *candidates: str) -> int | None:
    for c in candidates:
        norm = " ".join(c.strip().lower().replace("\n", " ").split())
        if norm in hdr:
            return hdr[norm]
    return None


def read_col(row, hdr: dict, *candidates, default=None):
    idx = col(hdr, *candidates)
    if idx is None:
        return default
    val = row.iloc[idx] if hasattr(row, "iloc") else row[idx]
    if pd.isna(val):
        return default
    return val
