# Uganda Pharma Sales Dashboard — Complete Build Guide

## How to Use This Document

You are a fresh Claude instance. This document is your complete specification to build the **Uganda Pharma Sales Intelligence Dashboard 2026** from scratch. The project uses **FastAPI (Python) + React 18** and is modelled after a similar IVC Ivory Coast dashboard.

**Read this entire document before writing any code.** Then follow the steps in order.

---

## STEP 0 — Read the Data Files Before Writing Any Code

This is the most important step. The Uganda data files are in the same folder as this document. Before writing `constants.py`, `name_map.py`, or any loader, you must **open and inspect every Excel file** to discover:

1. **Product names** — exact strings as they appear in the PRODUCT column of the sales file
2. **Delegate / MR names** — exact strings from monthly reports and visit tracker sheets
3. **Territory / area names** — exact strings from the delegates and tour plan files
4. **Distributor names** — exact column header prefixes in the sales file (e.g. "AMSCO", "CIPLA", "ABACUS")
5. **Currency** — check if the files use UGX (Uganda Shillings). Default assumption: `1 EUR = 3800 UGX`. If the files contain a different rate, use that.
6. **Activity types** — exact strings from the expense and activity plan files
7. **Tab names** — exact sheet/tab names in every Excel file (they may differ from IVC)
8. **Column headers** — exact column names in every tab (they may differ from IVC)

Use `pandas` to inspect files:

```python
import pandas as pd

# List all tabs
xl = pd.ExcelFile("Uganda_Sales_Apr_2026.xlsx")
print(xl.sheet_names)

# Read the first few rows of a tab
df = pd.read_excel("Uganda_Sales_Apr_2026.xlsx", sheet_name=0, header=None)
print(df.head(10))
```

**Build your `name_map.py` and `constants.py` entirely from what you find in Step 0.** Do not guess names.

---

## Architecture

```
uganda-sales-dashboard/
├── backend/
│   ├── main.py
│   ├── loaders.py
│   ├── constants.py
│   ├── name_map.py          ← MINIMAL: exact dicts only, no fuzzy matching
│   ├── utils.py
│   ├── insights_builder.py
│   ├── requirements.txt
│   ├── .env
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── local.py
│   ├── cache/
│   │   ├── __init__.py
│   │   └── redis_client.py
│   └── routers/
│       ├── __init__.py
│       ├── overview.py
│       ├── months.py
│       ├── products.py
│       ├── delegates.py
│       ├── expenses.py
│       ├── activities.py
│       └── insights.py
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       ├── context/
│       │   └── FilterContext.jsx
│       ├── hooks/
│       │   └── useDashboard.js
│       ├── utils/
│       │   ├── chartConfig.js
│       │   └── monthConfig.js
│       ├── components/
│       │   ├── KpiCard.jsx
│       │   ├── ChartCard.jsx
│       │   ├── DataTable.jsx
│       │   ├── Badge.jsx
│       │   ├── SectionLabel.jsx
│       │   ├── InsightBox.jsx
│       │   ├── TabBar.jsx
│       │   ├── FilterBar.jsx
│       │   ├── SalesOutcomeCell.jsx
│       │   ├── TourPlanSection.jsx
│       │   └── VisitTrackerSection.jsx
│       └── tabs/
│           ├── OverviewTab.jsx
│           ├── MonthTab.jsx
│           ├── ProductsTab.jsx
│           ├── DelegatesTab.jsx
│           ├── ExpensesTab.jsx
│           ├── ActivitiesTab.jsx
│           └── NomenclatureTab.jsx
├── UGANDA/                  ← data files go here
│   └── April/
│       ├── Uganda_Sales_Apr_2026.xlsx
│       ├── Uganda_Projection_Apr_2026.xlsx
│       ├── Uganda_Expense_Apr_2026.xlsx
│       ├── Uganda_Monthly_Reports_Apr_2026.xlsx
│       ├── Uganda_Visit_Tracker_Apr_2026.xlsx
│       └── Uganda_Tour_Plan_Apr_2026.xlsx
└── start.sh
```

**Data folder**: place all Uganda Excel files in `UGANDA/` at the project root, with one subfolder per month (e.g. `April/`). The master sales file (with all months' sales tabs and annual projections) goes in `UGANDA/` root.

---

## BACKEND

### `backend/requirements.txt`

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
pandas==2.2.2
openpyxl==3.1.2
python-dotenv==1.0.1
httpx==0.27.0
redis==5.0.4
groq==0.9.0
rapidfuzz==3.9.3
```

> Note: `rapidfuzz` is listed but should NOT be used in `name_map.py`. It is only here in case you need it elsewhere. The name_map uses exact dicts only.

---

### `backend/constants.py`

```python
"""
Shared constants for Uganda Pharma Dashboard.
Fill DISTRIBUTORS from what you find in the sales file headers (Step 0).
"""

# Uganda Shillings to EUR conversion rate
# Check the data files — if no rate is given, 3800 is the standard approximation
UGX_TO_EUR = 3800.0

# Fill these from the sales file column headers discovered in Step 0
# Example: ["AMSCO", "CIPLA", "ABACUS", "LABOREX"] — replace with actual values
DISTRIBUTORS = []  # ← populate from Step 0

# IDs excluded from field-MR performance tables (country managers, agents, etc.)
# Populate from what you find in the delegate data
_NON_MR_IDS: set = set()

# Color palette
CLR_GREEN  = "#00C49A"
CLR_RED    = "#FF4C61"
CLR_BLUE   = "#4C9FFF"
CLR_ORANGE = "#FF9F40"
CLR_PURPLE = "#B57BFF"
CLR_TEAL   = "#26C6DA"
CLR_YELLOW = "#FFD166"

# Map distributor name → color (fill after you know DISTRIBUTORS)
DIST_COLORS: dict = {}
```

---

### `backend/utils.py`

```python
import math
import pandas as pd


def safe_num(val, default=0.0):
    """Convert any value to float, return default on failure."""
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def _parse_header(row) -> dict[str, int]:
    """
    Given a pandas Series (one header row), return {normalised_key: col_index}.
    Normalisation: lowercase, strip, collapse whitespace, remove newlines.
    """
    result = {}
    for i, val in enumerate(row):
        if pd.isna(val):
            continue
        key = str(val).strip().lower().replace("\n", " ")
        key = " ".join(key.split())
        result[key] = i
    return result


def col(hdr: dict, *candidates: str) -> int | None:
    """Return the first column index matching any candidate key, or None."""
    for c in candidates:
        norm = " ".join(c.strip().lower().replace("\n", " ").split())
        if norm in hdr:
            return hdr[norm]
    return None


def read_col(row, hdr: dict, *candidates, default=None):
    """Read a cell value from a row using candidate column names."""
    idx = col(hdr, *candidates)
    if idx is None:
        return default
    val = row.iloc[idx] if hasattr(row, "iloc") else row[idx]
    if pd.isna(val):
        return default
    return val
```

---

### `backend/name_map.py`  ← MINIMAL

**Critical rule**: This file uses **exact string matching only**. No fuzzy matching. No auto-registry. No `rapidfuzz`. The Uganda data comes from an automated system — names are consistent. If a name is not in the dict, return the raw value as-is so it remains visible in the UI.

Build every dict below using the actual names you found in Step 0.

```python
"""
Name normalisation for Uganda Dashboard.
EXACT-MATCH ONLY — data is system-generated, names are consistent.
Unknown values pass through as raw strings (never replaced with 'UNKNOWN').
"""

# ── Delegates / MRs ──────────────────────────────────────────────────────────
# Build from: Monthly Reports → DELEGATES tab, Visit Tracker sheet names
# Format: {"exact name as in file": "MR_001", ...}
# Assign sequential IDs MR_001, MR_002, … in the order they appear
MR_CANONICAL: dict[str, str] = {
    # "JOHN DOE": "MR_001",
    # "JANE SMITH": "MR_002",
}

# Display names: ID → full display name
MR_DISPLAY: dict[str, str] = {v: k for k, v in MR_CANONICAL.items()}

# Short names (first name only, for compact labels)
MR_SHORT: dict[str, str] = {
    # "MR_001": "JOHN",
}

# Joint entries (if tour plan has combined names like "JOHN/JANE")
MR_JOINT_MAP: dict[str, list[str]] = {
    # "JOHN/JANE": ["MR_001", "MR_002"],
}


def normalize_mr(raw: str) -> str:
    """Return MR ID for raw name. Falls back to raw string if not found."""
    if not raw or (isinstance(raw, float)):
        return ""
    s = str(raw).strip().upper()
    for pattern, ids in MR_JOINT_MAP.items():
        if pattern.upper() in s or s in pattern.upper():
            return ",".join(ids)
    return MR_CANONICAL.get(s, raw)


def mr_display_name(mr_id: str) -> str:
    """Return display name for an MR ID (or comma-separated IDs)."""
    if "," in str(mr_id):
        return " + ".join(MR_DISPLAY.get(i.strip(), i.strip()) for i in mr_id.split(","))
    return MR_DISPLAY.get(mr_id, mr_id)


def mr_short_name(mr_id: str) -> str:
    return MR_SHORT.get(mr_id, mr_display_name(mr_id).split()[0] if mr_display_name(mr_id) else mr_id)


# ── Products ─────────────────────────────────────────────────────────────────
# Build from: Sales file PRODUCT column, Projection file PRODUCT column
# Format: {"EXACT PRODUCT NAME": "P_001", ...}
PRODUCT_CANONICAL: dict[str, str] = {
    # "PRODUCT NAME": "P_001",
}

PRODUCT_DISPLAY: dict[str, str] = {v: k for k, v in PRODUCT_CANONICAL.items()}

# Category per product: "TABLET" or "INJECTABLE"
# Discover from the CATEGORY column in the sales file
PRODUCT_CATEGORIES: dict[str, str] = {
    # "P_001": "TABLET",
}


def normalize_product(raw: str) -> str:
    """Return product ID. Falls back to raw string if not found."""
    if not raw or (isinstance(raw, float)):
        return ""
    s = str(raw).strip().upper()
    return PRODUCT_CANONICAL.get(s, raw)


def product_display_name(product_id: str) -> str:
    return PRODUCT_DISPLAY.get(product_id, product_id)


def product_category(product_id: str) -> str:
    return PRODUCT_CATEGORIES.get(product_id, "UNKNOWN")


def parse_multi_products(raw_str: str) -> str:
    """Parse slash/comma separated product string → slash-separated display names."""
    if not raw_str:
        return ""
    parts = [p.strip() for p in str(raw_str).replace(",", "/").split("/") if p.strip()]
    names = [product_display_name(normalize_product(p)) for p in parts]
    return " / ".join(n for n in names if n)


# ── Activities ────────────────────────────────────────────────────────────────
# Build from: Expense file ACTIVITY TYPE column
ACTIVITY_CANONICAL: dict[str, str] = {
    # "COMMISSION": "ACT_COMMISSION",
    # "MOTIVATION": "ACT_MOTIVATION",
}

ACTIVITY_DISPLAY: dict[str, str] = {v: k for k, v in ACTIVITY_CANONICAL.items()}


def normalize_activity(raw: str) -> str:
    if not raw or (isinstance(raw, float)):
        return ""
    s = str(raw).strip().upper()
    return ACTIVITY_CANONICAL.get(s, raw)


def activity_display_name(act_id: str) -> str:
    return ACTIVITY_DISPLAY.get(act_id, act_id)


# ── Territories ───────────────────────────────────────────────────────────────
# Build from: Monthly Reports TERRITORY column, Tour Plan AREA column
TERRITORY_CANONICAL: dict[str, str] = {
    # "KAMPALA NORTH": "ZONE_KAM_N",
}

TERRITORY_DISPLAY: dict[str, str] = {v: k for k, v in TERRITORY_CANONICAL.items()}


def normalize_territory(raw: str) -> str:
    """Return zone ID. Falls back to title-cased raw string (not 'UNKNOWN')."""
    if not raw or (isinstance(raw, float)):
        return ""
    s = str(raw).strip().upper()
    return TERRITORY_CANONICAL.get(s, str(raw).strip().title())


def territory_display_name(zone_id: str) -> str:
    return TERRITORY_DISPLAY.get(zone_id, zone_id)


# ── Doctors ───────────────────────────────────────────────────────────────────
# Doctors come straight from the visit tracker — no normalisation needed.
def normalize_doctor(raw: str) -> str:
    if not raw or (isinstance(raw, float)):
        return ""
    return str(raw).strip().title()
```

---

### `backend/storage/base.py`

```python
from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    def get_file_bytes(self, relative_path: str) -> bytes:
        pass

    @abstractmethod
    def list_files(self, folder: str) -> list[str]:
        pass

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        pass
```

### `backend/storage/__init__.py`

```python
import os
from .base import StorageBackend


def get_storage() -> StorageBackend:
    backend = os.getenv("STORAGE_BACKEND", "local")
    if backend == "local":
        from .local import LocalStorage
        return LocalStorage()
    raise ValueError(f"Unsupported STORAGE_BACKEND: {backend!r}")
```

### `backend/storage/local.py`

```python
import os
from pathlib import Path
from .base import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self):
        data_path = os.getenv("UGANDA_DATA_PATH", "../UGANDA")
        backend_dir = Path(__file__).parent.parent
        self.root = (backend_dir / data_path).resolve()

    def get_file_bytes(self, relative_path: str) -> bytes:
        full_path = self.root / relative_path
        with open(full_path, "rb") as f:
            return f.read()

    def list_files(self, folder: str) -> list[str]:
        folder_path = self.root / folder
        if not folder_path.exists():
            return []
        return os.listdir(folder_path)

    def exists(self, relative_path: str) -> bool:
        return os.path.exists(self.root / relative_path)
```

### `backend/storage/s3.py`

```python
from .base import StorageBackend


class S3Storage(StorageBackend):
    """Stub — not yet implemented."""
    def get_file_bytes(self, relative_path: str) -> bytes:
        raise NotImplementedError("S3 storage not implemented")

    def list_files(self, folder: str) -> list[str]:
        raise NotImplementedError

    def exists(self, relative_path: str) -> bool:
        raise NotImplementedError
```

---

### `backend/cache/redis_client.py`

Redis is optional. The app works without it; responses are just recomputed on every request.

```python
import os
import json
import asyncio

try:
    import redis.asyncio as aioredis
    _redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = aioredis.from_url(_redis_url, decode_responses=True)
except Exception:
    redis_client = None


async def health_check() -> bool:
    if redis_client is None:
        return False
    try:
        await asyncio.wait_for(redis_client.ping(), timeout=1.0)
        return True
    except Exception:
        return False


async def get_api_cache(key: str):
    if redis_client is None:
        return None
    try:
        raw = await redis_client.get(f"api:{key}")
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def set_api_cache(key: str, data, ttl: int = 3600):
    if redis_client is None:
        return
    try:
        await redis_client.setex(f"api:{key}", ttl, json.dumps(data))
    except Exception:
        pass


async def invalidate_api_keys(keys: list[str]):
    if redis_client is None:
        return
    try:
        pipe = redis_client.pipeline()
        for k in keys:
            pipe.delete(f"api:{k}")
        await pipe.execute()
    except Exception:
        pass


async def flush_all_api_cache():
    if redis_client is None:
        return
    try:
        keys = await redis_client.keys("api:*")
        if keys:
            await redis_client.delete(*keys)
    except Exception:
        pass


def build_sheet_dependencies(month_keys: list[str]) -> dict:
    """Maps a logical data key to list of API endpoints that depend on it."""
    deps = {
        "sales":      ["overview", "products"] + [f"months:{k}" for k in month_keys],
        "projection": ["overview", "products"] + [f"months:{k}" for k in month_keys],
        "expense":    ["expenses", "activities"] + [f"months:{k}" for k in month_keys],
        "monthly":    ["delegates", "overview"] + [f"months:{k}" for k in month_keys],
        "tour":       ["delegates"] + [f"months:{k}" for k in month_keys],
        "visits":     ["delegates"] + [f"months:{k}" for k in month_keys],
    }
    for k in month_keys:
        deps[f"month_{k}"] = [f"months:{k}", "overview", "products", "delegates", "expenses", "activities"]
    return deps
```

### `backend/cache/__init__.py`

Empty file.

---

### `backend/loaders.py`

**Important**: The column names below are educated guesses based on IVC patterns. After Step 0, update every `col(hdr, ...)` call to use the **exact column names from your Uganda files**.

```python
"""
Data loaders for Uganda Pharma Dashboard.
All loaders accept file_bytes (local mode).
IMPORTANT: Run Step 0 first to discover actual column names, then update
           every col(hdr, ...) call to match your Uganda Excel files.
"""

import io
import os
import re
from pathlib import Path

import pandas as pd

from constants import UGX_TO_EUR, DISTRIBUTORS
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


def _discover_month_folders(storage) -> list[tuple[str, str]]:
    """Return [(month_key, folder_name), ...] for all month folders found."""
    results = []
    try:
        root = storage.root
        for entry in sorted(os.scandir(root), key=lambda e: e.name):
            if entry.is_dir():
                name_lower = entry.name.lower()
                key = MONTH_FOLDER_MAP.get(name_lower)
                if key:
                    results.append((key, entry.name))
    except Exception as e:
        print(f"[loaders] Month discovery error: {e}")
    return results


def _find_root_file(storage, kind: str) -> bytes | None:
    """Find the master file in the UGANDA root. kind: 'sales'"""
    try:
        root = storage.root
        for entry in os.scandir(root):
            if entry.is_file() and entry.name.endswith(".xlsx"):
                name_lower = entry.name.lower()
                if kind == "sales" and "sales" in name_lower:
                    return storage.get_file_bytes(entry.name)
    except Exception as e:
        print(f"[loaders] Root file search error for {kind!r}: {e}")
    return None


def _find_month_file(storage, folder: str, kind: str) -> bytes | None:
    """Find a specific file type within a month subfolder."""
    kind_patterns = {
        "projection": ["projection", "proj"],
        "expense":    ["expense", "exp"],
        "monthly":    ["monthly", "report"],
        "visit":      ["visit", "tracker"],
        "tour":       ["tour", "plan"],
    }
    patterns = kind_patterns.get(kind, [kind])
    try:
        for fname in storage.list_files(folder):
            fname_lower = fname.lower()
            if fname_lower.endswith(".xlsx") and any(p in fname_lower for p in patterns):
                return storage.get_file_bytes(f"{folder}/{fname}")
    except Exception as e:
        print(f"[loaders] Month file search error ({kind} in {folder}): {e}")
    return None


# ── Canonical rate cache ──────────────────────────────────────────────────────

_canonical_rates: dict[str, float] = {}


def build_canonical_rates(sales_bytes: bytes):
    """Extract product to rate_eur from the master sales file."""
    global _canonical_rates
    try:
        xl = pd.ExcelFile(io.BytesIO(sales_bytes))
        df = xl.parse(xl.sheet_names[0], header=None)

        hdr_row = None
        for i, row in df.iterrows():
            vals = [str(v).upper() for v in row if pd.notna(v)]
            if any("product" in v.lower() for v in vals):
                hdr_row = i
                break
        if hdr_row is None:
            return

        hdr = _parse_header(df.iloc[hdr_row])
        product_col = col(hdr, "product")
        rate_col    = col(hdr, "rate (eur)", "rate\n(eur)", "rate(eur)", "rate eur", "rate")

        for _, row in df.iloc[hdr_row + 1:].iterrows():
            if product_col is None:
                break
            prod_raw = row.iloc[product_col] if hasattr(row, "iloc") else row[product_col]
            if pd.isna(prod_raw):
                continue
            prod_id = normalize_product(str(prod_raw).strip().upper())
            if rate_col is not None:
                rate = safe_num(row.iloc[rate_col] if hasattr(row, "iloc") else row[rate_col])
                if rate > 0:
                    _canonical_rates[prod_id] = rate
    except Exception as e:
        print(f"[loaders] build_canonical_rates error: {e}")


# ── Sales loader ──────────────────────────────────────────────────────────────

def load_sales(file_bytes: bytes, tab_name: str | None = None) -> dict:
    """
    Load a monthly sales tab.
    Returns {"current": DataFrame, "prev": DataFrame}.

    Expected columns (update after Step 0):
      S.NO, CATEGORY, PRODUCT, RATE (EUR),
      {DISTRIBUTOR} SALES, {DISTRIBUTOR} CLOSING, {DISTRIBUTOR} ORDER

    Output DataFrame columns:
      Product, Category, RATE,
      {DIST}_SALES, {DIST}_CLOSING, {DIST}_ORDER,
      TOTAL_SALES, TOTAL_VALUE_EUR, {DIST}_SALES_EUR
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
        current_category = ""
        for _, row in raw.iloc[hdr_row + 1:].iterrows():
            sno_idx = col(hdr, "s.no", "s no", "sno", "no")
            sno_val = row.iloc[sno_idx] if sno_idx is not None else None
            try:
                sno_int = int(float(str(sno_val))) if pd.notna(sno_val) else None
            except (ValueError, TypeError):
                sno_int = None
            if sno_int is None or sno_int > 50:
                continue

            prod_idx = col(hdr, "product")
            cat_idx  = col(hdr, "category")
            rate_idx = col(hdr, "rate (eur)", "rate\n(eur)", "rate eur", "rate")

            if cat_idx is not None and pd.notna(row.iloc[cat_idx]):
                current_category = str(row.iloc[cat_idx]).strip().upper()

            prod_raw = row.iloc[prod_idx] if prod_idx is not None else None
            if pd.isna(prod_raw):
                continue

            prod_id = normalize_product(str(prod_raw).strip().upper())
            rate = _canonical_rates.get(prod_id, safe_num(row.iloc[rate_idx] if rate_idx is not None else 0))
            category = product_category(prod_id) or current_category

            entry = {
                "Product":  product_display_name(prod_id),
                "Category": category,
                "RATE":     rate,
            }

            total_sales = 0.0
            for dist in DISTRIBUTORS:
                dist_upper = dist.upper()
                s_idx = col(hdr, f"{dist_upper} sales",  f"{dist} sales")
                c_idx = col(hdr, f"{dist_upper} closing", f"{dist} closing")
                o_idx = col(hdr, f"{dist_upper} order",   f"{dist} order")

                sales_val   = safe_num(row.iloc[s_idx] if s_idx is not None else None)
                closing_val = safe_num(row.iloc[c_idx] if c_idx is not None else None)
                order_val   = safe_num(row.iloc[o_idx] if o_idx is not None else None)

                entry[f"{dist}_SALES"]   = sales_val
                entry[f"{dist}_CLOSING"] = closing_val
                entry[f"{dist}_ORDER"]   = order_val
                total_sales += sales_val

            entry["TOTAL_SALES"]     = total_sales
            entry["TOTAL_VALUE_EUR"] = total_sales * rate
            for dist in DISTRIBUTORS:
                entry[f"{dist}_SALES_EUR"] = entry[f"{dist}_SALES"] * rate

            rows.append(entry)

        df_current = pd.DataFrame(rows)
        return {"current": df_current, "prev": pd.DataFrame()}

    except Exception as e:
        print(f"[loaders] load_sales error: {e}")
        return {"current": pd.DataFrame(), "prev": pd.DataFrame()}
```

---

### `backend/loaders.py` (continued)

```python
# ── Projection loader ─────────────────────────────────────────────────────────

def load_projection(file_bytes: bytes) -> dict:
    """
    Load projection file.
    Expected tabs (update after Step 0): PROJECTION, ACTIVITY PLAN
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheets_lower = {s.lower(): s for s in xl.sheet_names}

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
            sno_idx = col(hdr, "s.no", "s no", "sno", "no")
            sno_val = row.iloc[sno_idx] if sno_idx is not None else None
            try:
                sno_int = int(float(str(sno_val))) if pd.notna(sno_val) else None
            except (ValueError, TypeError):
                sno_int = None
            if sno_int is None or sno_int > 50:
                continue

            prod_idx  = col(hdr, "product")
            cat_idx   = col(hdr, "category")
            rate_idx  = col(hdr, "rate (eur)", "rate\n(eur)", "rate eur", "rate")
            tgt_u_idx = col(hdr, "target units", "target\nunits")
            tgt_v_idx = col(hdr, "target value (eur)", "target value\n(eur)", "target value eur")

            prod_raw = row.iloc[prod_idx] if prod_idx is not None else None
            if pd.isna(prod_raw):
                continue

            prod_id   = normalize_product(str(prod_raw).strip().upper())
            rate      = _canonical_rates.get(prod_id, safe_num(row.iloc[rate_idx] if rate_idx is not None else 0))
            tgt_units = safe_num(row.iloc[tgt_u_idx] if tgt_u_idx is not None else None)
            tgt_val   = safe_num(row.iloc[tgt_v_idx]) if tgt_v_idx is not None else tgt_units * rate

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
                if any("doctor" in v or "delegate" in v for v in vals):
                    hdr_row_a = i
                    break

            hdr_a = _parse_header(raw_act.iloc[hdr_row_a])
            act_rows = []
            for _, row in raw_act.iloc[hdr_row_a + 1:].iterrows():
                doc_idx  = col(hdr_a, "doctor / contact", "doctor/contact", "doctor", "contact")
                del_idx  = col(hdr_a, "delegate", "mr", "responsible")
                hosp_idx = col(hdr_a, "hospital / clinic", "hospital/clinic", "hospital", "clinic")
                spec_idx = col(hdr_a, "speciality", "specialty")
                area_idx = col(hdr_a, "area", "territory", "zone")
                act_idx  = col(hdr_a, "activity type", "activity")
                amt_idx  = col(hdr_a, "amount (ugx)", "amount(ugx)", "amount (fcfa)", "amount")
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

                del_raw  = row.iloc[del_idx] if del_idx is not None else None
                act_raw  = row.iloc[act_idx] if act_idx is not None else None
                area_raw = row.iloc[area_idx] if area_idx is not None else None
                fp_raw   = row.iloc[fp_idx] if fp_idx is not None else None

                act_rows.append({
                    "SN":           sn,
                    "Doctor":       normalize_doctor(str(doc_raw).strip()) if pd.notna(doc_raw) else "",
                    "Hospital":     str(row.iloc[hosp_idx]).strip() if hosp_idx is not None and pd.notna(row.iloc[hosp_idx]) else "",
                    "Speciality":   str(row.iloc[spec_idx]).strip() if spec_idx is not None and pd.notna(row.iloc[spec_idx]) else "",
                    "Delegate":     normalize_mr(str(del_raw).strip().upper()) if pd.notna(del_raw) else "",
                    "Area":         normalize_territory(str(area_raw).strip().upper()) if pd.notna(area_raw) else "",
                    "Activity":     activity_display_name(normalize_activity(str(act_raw).strip().upper())) if pd.notna(act_raw) else "",
                    "Amount_UGX":   safe_num(row.iloc[amt_idx] if amt_idx is not None else None),
                    "Focus_Products": parse_multi_products(str(fp_raw)) if pd.notna(fp_raw) else "",
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
    Expected tabs (update after Step 0): MONEY RECEIVED, ACTIVITY EXPENSES, OTHER EXPENSES
    Currency: UGX. Divide by UGX_TO_EUR to get EUR.
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheets_lower = {s.lower(): s for s in xl.sheet_names}
        missing = []

        # ── Money Received ──
        mr_sheet = (
            sheets_lower.get("money received") or
            sheets_lower.get("money") or
            sheets_lower.get("budget")
        )
        opening_balance_ugx = new_budget_ugx = total_spent_ugx = balance_ugx = 0.0
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
            amt_ugx_idx = col(hdr, "amount (ugx)", "amount(ugx)", "amount (fcfa)", "amount")
            date_idx    = col(hdr, "date")
            src_idx     = col(hdr, "source / description", "description", "source")
            notes_idx   = col(hdr, "notes", "remarks")

            mr_rows = []
            for _, row in raw_mr.iloc[hdr_row + 1:].iterrows():
                type_raw = row.iloc[type_idx] if type_idx is not None else None
                amt_raw  = row.iloc[amt_ugx_idx] if amt_ugx_idx is not None else None
                if pd.isna(type_raw) and pd.isna(amt_raw):
                    continue

                type_str = str(type_raw).strip().upper() if pd.notna(type_raw) else ""
                amt = safe_num(amt_raw)

                if "opening" in type_str:
                    opening_balance_ugx = amt
                elif "received" in type_str:
                    new_budget_ugx += amt
                elif "spent" in type_str:
                    total_spent_ugx += amt
                elif "balance" in type_str:
                    balance_ugx = amt

                date_val  = row.iloc[date_idx]  if date_idx  is not None else None
                src_val   = row.iloc[src_idx]   if src_idx   is not None else None
                notes_val = row.iloc[notes_idx] if notes_idx is not None else None

                mr_rows.append({
                    "Type":       type_str,
                    "Date":       pd.to_datetime(date_val, errors="coerce") if pd.notna(date_val) else None,
                    "Source":     str(src_val).strip()   if pd.notna(src_val)   else "",
                    "Amount_UGX": amt,
                    "Amount_EUR": amt / UGX_TO_EUR,
                    "Notes":      str(notes_val).strip() if pd.notna(notes_val) else "",
                })
            df_mr = pd.DataFrame(mr_rows)
        else:
            missing.append("MONEY RECEIVED")

        total_received_ugx = opening_balance_ugx + new_budget_ugx

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
                if any("doctor" in v or "activity" in v for v in vals):
                    hdr_row_ae = i
                    break

            hdr_ae   = _parse_header(raw_ae.iloc[hdr_row_ae])
            sno_idx  = col(hdr_ae, "s.no", "s no", "sno", "no")
            doc_idx  = col(hdr_ae, "doctor / contact", "doctor/contact", "doctor", "contact")
            hosp_idx = col(hdr_ae, "hospital / clinic", "hospital/clinic", "hospital")
            spec_idx = col(hdr_ae, "speciality", "specialty")
            act_idx  = col(hdr_ae, "activity type", "activity")
            prod_idx = col(hdr_ae, "products", "focus products", "product")
            amt_idx  = col(hdr_ae, "amount (ugx)", "amount(ugx)", "amount (fcfa)", "amount")
            resp_idx = col(hdr_ae, "responsible", "delegate", "mr")
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
                amt_ugx  = safe_num(row.iloc[amt_idx] if amt_idx is not None else None)
                prod_raw = row.iloc[prod_idx] if prod_idx is not None else None
                out_raw  = row.iloc[out_idx]  if out_idx  is not None else None
                vis_raw  = row.iloc[vis_idx]  if vis_idx  is not None else None

                sales_outcome = []
                outcome_eur = 0.0
                if pd.notna(out_raw) and str(out_raw).strip():
                    for part in str(out_raw).split("|"):
                        part = part.strip()
                        if ":" in part:
                            p_name, qty_str = part.split(":", 1)
                            p_id = normalize_product(p_name.strip().upper())
                            try:
                                qty = int(float(qty_str.strip()))
                            except (ValueError, TypeError):
                                qty = 0
                            rate = _canonical_rates.get(p_id, 0.0)
                            eur_val = qty * rate
                            outcome_eur += eur_val
                            sales_outcome.append({
                                "product_id":   p_id,
                                "product_name": product_display_name(p_id),
                                "qty":          qty,
                                "rate_eur":     rate,
                                "eur_value":    eur_val,
                            })

                resp_str = str(resp_raw).strip().upper() if pd.notna(resp_raw) else ""
                mr_ids   = [normalize_mr(r.strip()) for r in resp_str.replace("/", ",").split(",") if r.strip()]
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
                    "Activity":         activity_display_name(normalize_activity(str(act_raw).strip().upper())) if pd.notna(act_raw) else "",
                    "Activity_ID":      normalize_activity(str(act_raw).strip().upper()) if pd.notna(act_raw) else "",
                    "Products":         parse_multi_products(str(prod_raw)) if pd.notna(prod_raw) else "",
                    "Amount_UGX":       amt_ugx,
                    "Amount_EUR":       amt_ugx / UGX_TO_EUR,
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
            sheets_lower.get("other expenses") or
            sheets_lower.get("other exp")
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
                amt_idx = col(hdr_oe, "amount (ugx)", "amount(ugx)", "amount (fcfa)", "amount")
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

                amt_ugx = safe_num(amt_raw)
                oe_rows.append({
                    "SN":         sn,
                    "Country":    str(row.iloc[cty_idx]).strip() if cty_idx is not None and pd.notna(row.iloc[cty_idx]) else "",
                    "Details":    str(det_raw).strip() if pd.notna(det_raw) else "",
                    "Amount_UGX": amt_ugx,
                    "Amount_EUR": amt_ugx / UGX_TO_EUR,
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
            "opening_balance_ugx": opening_balance_ugx,
            "new_budget_ugx":      new_budget_ugx,
            "total_received_ugx":  total_received_ugx,
            "total_spent_ugx":     total_spent_ugx,
            "balance_ugx":         balance_ugx,
            "opening_balance_eur": opening_balance_ugx / UGX_TO_EUR,
            "new_budget_eur":      new_budget_ugx      / UGX_TO_EUR,
            "total_received_eur":  total_received_ugx  / UGX_TO_EUR,
            "total_spent_eur":     total_spent_ugx     / UGX_TO_EUR,
            "balance_eur":         balance_ugx         / UGX_TO_EUR,
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
```

```python
# ── Monthly Reports loader ────────────────────────────────────────────────────

def load_monthly_reports(file_bytes: bytes) -> dict:
    """
    Load monthly reports file.
    Expected tabs (update after Step 0): DELEGATES, BUDGET ANALYSIS
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
            vals = [str(v).lower() for v in row if pd.notna(v)]
            if any("delegate" in v or "territory" in v or "name" in v for v in vals):
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
            ctc_idx  = col(hdr, "ctc\n(eur)", "ctc (eur)", "ctc")
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
                "CTC":            safe_num(row.iloc[ctc_idx] if ctc_idx is not None else None),
                "DrInList":       int(safe_num(row.iloc[dil_idx] if dil_idx is not None else None)) or None,
                "ListedDRCovered": int(safe_num(row.iloc[ldc_idx] if ldc_idx is not None else None)) or None,
                "PctDRCovered":   pct_dr,
            })

        df_del = pd.DataFrame(del_rows)

        ba_sheet = (
            sheets_lower.get("budget analysis") or
            sheets_lower.get("budget")
        )
        df_ba = pd.DataFrame()
        if ba_sheet:
            raw_ba = xl.parse(ba_sheet, header=None)
            hdr_row_ba = 0
            for i, row in raw_ba.iterrows():
                vals = [str(v).lower() for v in row if pd.notna(v)]
                if any("doctor" in v or "activity" in v for v in vals):
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
                    "ActivityType": activity_display_name(normalize_activity(str(act_raw).strip().upper())) if pd.notna(act_raw) else "",
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
    Load visit tracker file. One sheet per MR.
    Output columns: MR_ID, MR, Doctor, Speciality, Clinic, Visit_Date, Month
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

            mr_raw_from_sheet = sheet_name.strip().upper()
            cell_name = None
            for r in range(min(3, len(raw))):
                for c_i in range(min(5, len(raw.columns))):
                    val = raw.iloc[r, c_i]
                    if pd.notna(val) and str(val).strip():
                        cell_val = str(val).strip().upper()
                        if any(ch.isalpha() for ch in cell_val) and len(cell_val) > 3:
                            cell_name = cell_val
                            break
                if cell_name:
                    break

            mr_raw   = cell_name or mr_raw_from_sheet
            mr_id    = normalize_mr(mr_raw)
            mr_disp  = mr_display_name(mr_id)

            hdr_row_v = 3
            for i in range(min(6, len(raw))):
                vals = [str(v).lower() for v in raw.iloc[i] if pd.notna(v)]
                if any("doctor" in v or "name" in v for v in vals):
                    hdr_row_v = i
                    break

            hdr = _parse_header(raw.iloc[hdr_row_v])
            doc_idx  = col(hdr, "doctor name", "doctor", "name")
            spec_idx = col(hdr, "speciality", "specialty", "specialization")
            clin_idx = col(hdr, "hospital/clinic", "hospital / clinic", "clinic", "hospital")

            date_cols = []
            for key, idx in hdr.items():
                if re.match(r'\d{1,2}[/\-]\d{1,2}', key) or re.match(r'\d{4}[/\-]', key):
                    date_cols.append(idx)
                elif key.startswith("date") or "visit" in key:
                    date_cols.append(idx)

            for _, row in raw.iloc[hdr_row_v + 1:].iterrows():
                doc_raw = row.iloc[doc_idx] if doc_idx is not None else None
                if pd.isna(doc_raw):
                    continue

                spec = str(row.iloc[spec_idx]).strip() if spec_idx is not None and pd.notna(row.iloc[spec_idx]) else ""
                clin = str(row.iloc[clin_idx]).strip() if clin_idx is not None and pd.notna(row.iloc[clin_idx]) else ""
                doctor = normalize_doctor(str(doc_raw).strip())

                if date_cols:
                    for dc in date_cols:
                        cell = row.iloc[dc] if dc < len(row) else None
                        if pd.notna(cell) and str(cell).strip() not in ("", "0", "nan"):
                            parsed_date = pd.to_datetime(cell, errors="coerce", dayfirst=True)
                            if pd.isna(parsed_date):
                                continue
                            all_rows.append({
                                "MR_ID":      mr_id,
                                "MR":         mr_disp,
                                "Doctor":     doctor,
                                "Speciality": spec,
                                "Clinic":     clin,
                                "Visit_Date": parsed_date,
                                "Month":      month_key,
                            })
                else:
                    all_rows.append({
                        "MR_ID":      mr_id,
                        "MR":         mr_disp,
                        "Doctor":     doctor,
                        "Speciality": spec,
                        "Clinic":     clin,
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
    return bool(p_words & a_words)


def load_tour_plan(file_bytes: bytes) -> pd.DataFrame:
    """
    Load tour plan file.
    Output columns: Date, MR, MR_Raw, Joint_Working, Planned_Area, Actual_Area, Covered
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheets_lower = {s.lower(): s for s in xl.sheet_names}
        sheet = (
            sheets_lower.get("tour plan") or
            sheets_lower.get("tour") or
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
    """Load ANNUAL PROJECTIONS tab from the master sales file. Returns {} if tab absent."""
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheets_lower = {s.lower(): s for s in xl.sheet_names}
        sheet = sheets_lower.get("annual projections") or sheets_lower.get("annual")
        if not sheet:
            return {}

        raw = xl.parse(sheet, header=None)
        month_header_row = raw.iloc[0]
        month_col_indices = []
        for i, val in enumerate(month_header_row):
            if pd.notna(val):
                s = str(val).lower()
                if re.match(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', s):
                    month_col_indices.append(i)

        result = {}
        for _, row in raw.iloc[1:].iterrows():
            prod_raw = row.iloc[0] if len(row) > 0 else None
            if pd.isna(prod_raw):
                continue
            prod_id    = normalize_product(str(prod_raw).strip().upper())
            annual_eur = sum(safe_num(row.iloc[i]) for i in month_col_indices if i < len(row))
            if annual_eur > 0:
                result[product_display_name(prod_id)] = annual_eur
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

        sales_b = _find_month_file(storage, folder_name, "sales")
        if not sales_b:
            if sales_bytes:
                tab = f"{month_key.upper()}-26"
                month_data["sales"] = load_sales(sales_bytes, tab_name=tab)
            else:
                month_data["sales"] = {"current": pd.DataFrame(), "prev": pd.DataFrame()}
        else:
            month_data["sales"] = load_sales(sales_b)

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
        print(f"[loaders]   OK {month_key}: sales={len(month_data['sales']['current'])} products, visits={len(month_data['visits'])}")

    return data
```

---

### `backend/insights_builder.py`

```python
import os


def build_insights_prompt(data: dict, annual_projections: dict) -> str:
    lines = ["Uganda Pharma Sales Dashboard — Data Summary\n"]
    for month_key, mdata in data.items():
        sales = mdata.get("sales", {})
        df = sales.get("current")
        if df is not None and not df.empty and "TOTAL_VALUE_EUR" in df.columns:
            total_eur = df["TOTAL_VALUE_EUR"].sum()
            lines.append(f"Month {month_key.upper()}: Total Sales EUR {total_eur:.0f}")
    return "\n".join(lines)


async def generate_insights(data: dict, annual_projections: dict) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return "AI insights unavailable — set GROQ_API_KEY in .env"
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        prompt = build_insights_prompt(data, annual_projections)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": (
                    "You are a pharma sales analyst. Given the Uganda sales data summary, "
                    "produce 4-6 concise action points. Each must start with a type tag: "
                    "[GOOD], [WARN], [DANGER], or [INFO]. Keep each point under 2 sentences."
                )},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Insights generation failed: {e}"
```

### `backend/routers/__init__.py`

Empty file.

---

### `backend/routers/overview.py`

```python
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


@router.get("/overview")
async def get_overview():
    cached = await get_api_cache("overview")
    if cached:
        return cached

    data               = app_state.get("data", {})
    annual_projections = app_state.get("annual_projections", {})

    month_sales: dict[str, float] = {}
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
        month_achievement[month_key] = (total_sales / total_proj * 100) if total_proj else 0.0

        visits_df   = mdata.get("visits")
        visits_count = len(visits_df) if visits_df is not None and not visits_df.empty else 0
        month_visits[month_key] = visits_count

        drs_conv  = 0
        avg_calls = 0.0
        if monthly is not None and not monthly.empty:
            drs_conv  = int(safe_num(monthly["DrsConverted"].sum())) if "DrsConverted" in monthly.columns else 0
            avg_calls = safe_num(monthly["AvgCallsPerDay"].mean())   if "AvgCallsPerDay" in monthly.columns else 0.0
        month_drs[month_key]       = drs_conv
        month_avg_calls[month_key] = avg_calls

        top_prod = ""
        if sales_df is not None and not sales_df.empty and "TOTAL_VALUE_EUR" in sales_df.columns:
            idx = sales_df["TOTAL_VALUE_EUR"].idxmax()
            top_prod = sales_df.loc[idx, "Product"] if idx is not None else ""

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
            "activity_spent_eur": safe_num(exp.get("total_spent_eur", 0)),
            "top_product":       top_prod,
        })

    total_sales_all = sum(month_sales.values())
    annual_target   = sum(annual_projections.values()) if annual_projections else 0.0
    best_month      = max(month_sales, key=month_sales.get) if month_sales else ""
    top_prod_all    = max(product_totals, key=product_totals.get) if product_totals else ""

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
```

---

### `backend/routers/months.py`

```python
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

    total_visits   = len(visits_df) if visits_df is not None and not visits_df.empty else 0
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
        if proj_df is not None and not proj_df.empty and "Product" in proj_df.columns:
            for _, r in proj_df.iterrows():
                proj_map[r["Product"]] = safe_num(r.get("Target_Value_EUR", 0))
        for _, r in sales_df.sort_values("TOTAL_VALUE_EUR", ascending=False).iterrows():
            prod = r.get("Product", "")
            product_sales.append({"product": prod, "sales_eur": safe_num(r.get("TOTAL_VALUE_EUR", 0)), "target_eur": proj_map.get(prod, 0.0)})

    from constants import DISTRIBUTORS
    distributor_sales = []
    if sales_df is not None and not sales_df.empty:
        for dist in DISTRIBUTORS:
            col_name = f"{dist}_SALES_EUR"
            val = safe_num(sales_df[col_name].sum()) if col_name in sales_df.columns else 0.0
            distributor_sales.append({"distributor": dist, "sales_eur": val})

    delegate_table = []
    if monthly is not None and not monthly.empty:
        for _, r in monthly.iterrows():
            del_id   = r.get("Delegate", "")
            del_name = mr_display_name(del_id) if del_id else r.get("Delegate_Raw", "")
            orders   = safe_num(r.get("TotalOrders", 0))
            ctc_val  = safe_num(r.get("CTC", 0))
            delegate_table.append({
                "name":          del_name,
                "territory":     r.get("Territory", ""),
                "total_calls":   int(safe_num(r.get("TotalCalls", 0))),
                "prescriber":    int(safe_num(r.get("Prescriber", 0))),
                "non_prescriber": int(safe_num(r.get("NonPrescriber", 0))),
                "pharmacy":      int(safe_num(r.get("PharmacyCalls", 0))),
                "drs_converted": int(safe_num(r.get("DrsConverted", 0))),
                "days_worked":   int(safe_num(r.get("DaysWorked", 0))),
                "avg_per_day":   safe_num(r.get("AvgCallsPerDay", 0)),
                "orders_eur":    orders or None,
                "ctc_eur":       ctc_val or None,
                "ctc_ratio":     (ctc_val / orders) if orders else None,
                "dr_in_list":    r.get("DrInList"),
                "listed_covered": r.get("ListedDRCovered"),
                "pct_listed":    r.get("PctDRCovered"),
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
        total_planned = len(tour_df)
        covered_count = int(tour_df["Covered"].sum()) if "Covered" in tour_df.columns else 0
        joint_count   = int((tour_df["Joint_Working"].str.strip() != "").sum()) if "Joint_Working" in tour_df.columns else 0

        tour_plan["summary"] = {
            "total": total_planned, "covered": covered_count,
            "uncovered": total_planned - covered_count,
            "coverage_pct": (covered_count / total_planned * 100) if total_planned else 0.0,
            "delegates_active": tour_df["MR"].nunique() if "MR" in tour_df.columns else 0,
            "joint_working": joint_count,
        }

        by_delegate = []
        for mr_id, grp in tour_df.groupby("MR"):
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

    visit_tracker = {"by_delegate": []}
    if visits_df is not None and not visits_df.empty:
        by_delegate_visits = []
        for mr_id, grp in visits_df.groupby("MR_ID"):
            mr_name = mr_display_name(mr_id) if mr_id else grp.iloc[0].get("MR", mr_id)
            visits  = [{"date": r["Visit_Date"].strftime("%Y-%m-%d") if pd.notna(r.get("Visit_Date")) else "",
                        "doctor": r.get("Doctor", ""), "speciality": r.get("Speciality", ""), "clinic": r.get("Clinic", "")}
                       for _, r in grp.iterrows()]
            by_delegate_visits.append({
                "mr": mr_name, "mr_id": mr_id,
                "total_visits": len(grp),
                "unique_doctors": grp["Doctor"].nunique() if "Doctor" in grp.columns else 0,
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
```

---

### `backend/routers/products.py`

```python
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
        annual_vs.append({"product": prod, "annual_target": annual_projections.get(prod), "ytd_achieved": ytd})
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
```

---

### `backend/routers/delegates.py`

```python
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
            "total_calls":      sum(d["q1"]["calls"] for d in delegates),
            "total_orders_eur": total_orders,
            "total_ctc_eur":    total_ctc,
            "overall_ctc_ratio": (total_ctc / total_orders) if total_orders else None,
        },
        "delegates": delegates,
    }

    await set_api_cache("delegates", result)
    return result
```

---

### `backend/routers/expenses.py`

```python
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
            "month":        MONTH_LABELS.get(month_key, month_key.title()),
            "received_ugx": safe_num(exp.get("total_received_ugx", 0)),
            "spent_ugx":    safe_num(exp.get("total_spent_ugx", 0)),
            "balance_ugx":  safe_num(exp.get("balance_ugx", 0)),
            "received_eur": safe_num(exp.get("total_received_eur", 0)),
            "spent_eur":    safe_num(exp.get("total_spent_eur", 0)),
            "balance_eur":  safe_num(exp.get("balance_eur", 0)),
        })

        month_exp_list = []
        if ae_df is not None and not ae_df.empty:
            for _, r in ae_df.iterrows():
                act     = r.get("Activity", "")
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
```

---

### `backend/routers/activities.py`

```python
from fastapi import APIRouter
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
                    "planned_ugx": 0.0, "actual_ugx": safe_num(r.get("Amount_UGX", 0)),
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
    for _, p_row in plan_df.iterrows():
        p_doc = str(p_row.get("Doctor", "")).lower()
        p_act = str(p_row.get("Activity", "")).lower()
        best  = None
        if actual_df is not None and not actual_df.empty:
            for a_idx, a_row in actual_df.iterrows():
                if a_idx in used_actual:
                    continue
                if str(a_row.get("Doctor", "")).lower() == p_doc and str(a_row.get("Activity", "")).lower() == p_act:
                    best = a_idx
                    break

        if best is not None:
            a_row = actual_df.loc[best]
            used_actual.add(best)
            actual_ugx  = safe_num(a_row.get("Amount_UGX", 0))
            planned_ugx = safe_num(p_row.get("Amount_UGX", 0))
            matched.append({
                "doctor": p_row.get("Doctor", ""), "hospital": p_row.get("Hospital", ""),
                "speciality": p_row.get("Speciality", ""),
                "delegate": mr_display_name(p_row.get("Delegate", "")),
                "area": p_row.get("Area", ""), "activity": p_row.get("Activity", ""),
                "activity_id": a_row.get("Activity_ID", ""),
                "focus_products": p_row.get("Focus_Products", ""),
                "planned_ugx": planned_ugx, "actual_ugx": actual_ugx,
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
                "area": p_row.get("Area", ""), "activity": p_row.get("Activity", ""),
                "focus_products": p_row.get("Focus_Products", ""),
                "planned_ugx": safe_num(p_row.get("Amount_UGX", 0)),
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
        "total_outcome_eur": 0.0, "planned_budget_ugx": 0.0, "actual_spent_ugx": 0.0,
        "with_outcome": 0, "without_outcome": 0,
    }

    for month_key, mdata in data.items():
        plan_df   = mdata.get("projection", {}).get("activity_plan")
        actual_df = mdata.get("expense", {}).get("activity_exp")
        matched, planned_not_done, unplanned = _match_activities(plan_df, actual_df)

        total_planned   = len(matched) + len(planned_not_done)
        executed_count  = len(matched)
        outcome_eur     = sum(r.get("sales_outcome_eur", 0) for r in matched)
        planned_budget  = sum(r.get("planned_ugx", 0) for r in matched) + sum(r.get("planned_ugx", 0) for r in planned_not_done)
        actual_spent    = sum(r.get("actual_ugx", 0) for r in matched) + sum(r.get("actual_ugx", 0) for r in unplanned)
        with_outcome    = sum(1 for r in matched if r.get("has_outcome"))

        by_month[month_key] = {
            "label": MONTH_LABELS.get(month_key, month_key.title()),
            "matched": matched, "planned_not_done": planned_not_done, "unplanned_done": unplanned,
            "summary": {
                "total_planned": total_planned, "executed": executed_count,
                "not_executed": len(planned_not_done), "unplanned": len(unplanned),
                "execution_rate_pct": (executed_count / total_planned * 100) if total_planned else 0.0,
                "planned_budget_ugx": planned_budget, "actual_spent_ugx": actual_spent,
                "total_outcome_eur": outcome_eur, "with_outcome": with_outcome,
                "without_outcome": executed_count - with_outcome,
            },
        }

        overall["total_planned"]     += total_planned
        overall["executed"]          += executed_count
        overall["not_executed"]      += len(planned_not_done)
        overall["unplanned"]         += len(unplanned)
        overall["total_outcome_eur"] += outcome_eur
        overall["planned_budget_ugx"] += planned_budget
        overall["actual_spent_ugx"]  += actual_spent
        overall["with_outcome"]      += with_outcome
        overall["without_outcome"]   += executed_count - with_outcome

    overall["execution_rate_pct"] = (overall["executed"] / overall["total_planned"] * 100) if overall["total_planned"] else 0.0

    result = {"months": list(by_month.keys()), "by_month": by_month, "overall": overall, "activity_breakdown": {}}
    await set_api_cache("activities", result)
    return result
```

---

### `backend/routers/insights.py`

```python
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from main import app_state
from cache.redis_client import get_api_cache, set_api_cache

router = APIRouter()
_insights_lock = asyncio.Lock()


def _parse_insights(raw: str) -> list[dict]:
    lines    = [l.strip() for l in raw.split("\n") if l.strip()]
    type_map = {"GOOD": "good", "WARN": "warn", "DANGER": "danger", "INFO": "info"}
    icon_map = {"good": "✓", "warn": "⚠", "danger": "✗", "info": "i"}
    results  = []
    for line in lines:
        t = "info"
        for tag, val in type_map.items():
            if f"[{tag}]" in line.upper():
                t = val
                line = line.replace(f"[{tag}]", "").replace(f"[{tag.lower()}]", "").strip()
                break
        results.append({"type": t, "icon": icon_map[t], "title": line[:60], "text": line})
    return results


@router.get("/insights")
async def get_insights(request: Request):
    cached = await get_api_cache("insights")
    if cached:
        return cached
    cached_text = app_state.get("insights_cache")
    if cached_text:
        result = {"insights": _parse_insights(cached_text), "cached": True}
        await set_api_cache("insights", result, ttl=7200)
        return result
    data   = app_state.get("data", {})
    annual = app_state.get("annual_projections", {})
    from insights_builder import generate_insights
    text = await generate_insights(data, annual)
    app_state["insights_cache"] = text
    result = {"insights": _parse_insights(text), "cached": False}
    await set_api_cache("insights", result, ttl=7200)
    return result


@router.post("/insights/refresh")
async def refresh_insights():
    if _insights_lock.locked():
        return JSONResponse(status_code=409, content={"status": "busy"})
    async with _insights_lock:
        app_state["insights_cache"] = None
        from cache.redis_client import invalidate_api_keys
        await invalidate_api_keys(["insights"])
        data   = app_state.get("data", {})
        annual = app_state.get("annual_projections", {})
        from insights_builder import generate_insights
        text = await generate_insights(data, annual)
        app_state["insights_cache"] = text
        result = {"insights": _parse_insights(text), "cached": False}
        await set_api_cache("insights", result, ttl=7200)
        return result
```

---

### `backend/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import sys
import os
import json
import math


class NaNSafeJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        def _fix(obj):
            if isinstance(obj, dict):
                return {k: _fix(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_fix(v) for v in obj]
            elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                return None
            return obj
        return json.dumps(_fix(content), ensure_ascii=False).encode("utf-8")


sys.path.insert(0, os.path.dirname(__file__))

from storage import get_storage

app_state = {}
_refresh_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from loaders import load_all_data, load_annual_projections, _find_root_file
    storage = get_storage()
    print("[startup] Loading Uganda data files...")
    data = load_all_data(storage)
    app_state["data"]    = data
    app_state["storage"] = storage

    sales_bytes = _find_root_file(storage, "sales")
    if sales_bytes:
        app_state["annual_projections"] = load_annual_projections(sales_bytes)
        print(f"[startup] Annual projections: {len(app_state['annual_projections'])} products")
    else:
        app_state["annual_projections"] = {}

    app_state["insights_cache"] = None
    print(f"[startup] Ready. Months loaded: {list(data.keys())}")
    yield
    app_state.clear()


app = FastAPI(
    title="Uganda Dashboard API",
    lifespan=lifespan,
    default_response_class=NaNSafeJSONResponse,
)

_extra_origins = [u.strip() for u in os.getenv("FRONTEND_URL", "").split(",") if u.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        *_extra_origins,
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import overview, months, products, delegates, expenses, insights, activities

app.include_router(overview.router,   prefix="/api")
app.include_router(months.router,     prefix="/api")
app.include_router(products.router,   prefix="/api")
app.include_router(delegates.router,  prefix="/api")
app.include_router(expenses.router,   prefix="/api")
app.include_router(insights.router,   prefix="/api")
app.include_router(activities.router, prefix="/api")


@app.get("/api/health")
def health():
    data = app_state.get("data", {})
    return {"status": "ok", "months_loaded": list(data.keys())}


@app.get("/api/months")
def available_months():
    return {"months": list(app_state.get("data", {}).keys())}


@app.post("/api/data/refresh")
async def refresh_data():
    if _refresh_lock.locked():
        return JSONResponse(status_code=409, content={"status": "busy"})
    async with _refresh_lock:
        from loaders import load_all_data, load_annual_projections, _find_root_file
        from cache.redis_client import flush_all_api_cache
        storage = app_state.get("storage")
        data    = load_all_data(storage)
        app_state["data"]           = data
        app_state["insights_cache"] = None
        sales_bytes = _find_root_file(storage, "sales")
        if sales_bytes:
            app_state["annual_projections"] = load_annual_projections(sales_bytes)
        await flush_all_api_cache()
        return {"status": "ok", "months_loaded": list(data.keys())}


@app.get("/api/cache/redisStatus")
async def redis_status():
    from cache.redis_client import health_check, redis_client
    ok = await health_check()
    if not ok:
        return {"redis_available": False}
    keys = await redis_client.keys("api:*")
    return {"redis_available": True, "cached_endpoints": len(keys), "keys": keys}
```

### `backend/.env` (template)

```
STORAGE_BACKEND=local
UGANDA_DATA_PATH=../UGANDA
GROQ_API_KEY=your_groq_key_here
REDIS_URL=redis://localhost:6379
FRONTEND_URL=
```

---

## FRONTEND

### `frontend/package.json`

```json
{
  "name": "uganda-sales-dashboard",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "chart.js": "^4.4.1",
    "react-chartjs-2": "^5.2.0",
    "chartjs-plugin-annotation": "^3.0.1",
    "@tanstack/react-query": "^5.40.0",
    "axios": "^1.7.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.2.0"
  }
}
```

### `frontend/vite.config.js`

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: true,
    proxy: { '/api': 'http://localhost:8000' }
  }
})
```

### `frontend/index.html`

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Uganda Sales Dashboard 2026</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

### `frontend/src/main.jsx`

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, Tooltip, Legend, Filler,
} from 'chart.js'
import AnnotationPlugin from 'chartjs-plugin-annotation'
import App from './App.jsx'
import './index.css'

ChartJS.register(
  CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, Tooltip, Legend, Filler, AnnotationPlugin,
)

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: Infinity, retry: 1 } },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
)
```

---

### `frontend/src/index.css`

Create a dark-theme CSS file with CSS variables. Key rules:

```css
:root {
  --bg:      #0a0d1a;
  --card:    #111320;
  --border:  #1e2340;
  --text:    #e8eaf6;
  --muted:   #6b7294;
  --accent:  #4C9FFF;
  --green:   #00C49A;
  --red:     #FF4C61;
  --orange:  #FF9F40;
  --purple:  #B57BFF;
  --teal:    #26C6DA;
  --yellow:  #FFD166;

  --apr: #4C9FFF;  --may: #00C49A;  --jun: #FF9F40;
  --jul: #B57BFF;  --aug: #FF4C61;  --sep: #26C6DA;
  --oct: #FFD166;  --nov: #7CB9E8;  --dec: #98D8C8;
  --jan: #F5CBA7;  --feb: #D7BDE2;  --mar: #A9CCE3;

  --font-body:    'Inter', sans-serif;
  --font-mono:    'IBM Plex Mono', monospace;
  --font-display: 'Syne', sans-serif;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: var(--font-body); min-height: 100vh; }

.app-shell  { max-width: 1440px; margin: 0 auto; padding: 24px 28px; }
.app-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.app-title  { font-family: var(--font-display); font-size: 1.6rem; font-weight: 800; }
.app-subtitle { color: var(--muted); font-size: 0.8rem; margin-top: 2px; }

.card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
.kpi  { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }
.kpi-card    { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }
.kpi-label   { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 6px; }
.kpi-value   { font-family: var(--font-mono); font-size: 1.5rem; font-weight: 600; }
.kpi-sub     { font-size: 0.75rem; color: var(--muted); margin-top: 4px; }
.kpi-change  { font-size: 0.75rem; margin-top: 4px; }
.kpi-change.up { color: var(--green); }
.kpi-change.dn { color: var(--red); }

.chart-card  { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
.chart-title { font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }
.chart-sub   { font-size: 0.75rem; color: var(--muted); margin-bottom: 14px; }
.h250 { height: 250px; } .h300 { height: 300px; } .h340 { height: 340px; }

.tbl-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; margin-bottom: 16px; }
.tbl-card table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.tbl-card th { background: #0d1025; padding: 10px 12px; text-align: left; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); border-bottom: 1px solid var(--border); }
.tbl-card td { padding: 9px 12px; border-bottom: 1px solid #151828; }
.tbl-card tr:last-child td { border-bottom: none; }
.tbl-card tr:hover td { background: #13172e; }
.tbl-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; border-bottom: 1px solid var(--border); }
.tbl-title  { font-size: 0.82rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }

.tab-bar { display: flex; gap: 4px; overflow-x: auto; padding-bottom: 4px; margin-bottom: 20px; scrollbar-width: none; }
.tab-bar::-webkit-scrollbar { display: none; }
.tab-btn { padding: 7px 16px; border-radius: 20px; border: 1px solid var(--border); background: transparent; color: var(--muted); font-size: 0.78rem; cursor: pointer; white-space: nowrap; transition: all 0.15s; }
.tab-btn:hover  { border-color: var(--accent); color: var(--text); }
.tab-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }

.badge   { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; font-family: var(--font-mono); }
.badge.g { background: rgba(0,196,154,0.15);  color: var(--green); }
.badge.d { background: rgba(255,76,97,0.15);   color: var(--red); }
.badge.w { background: rgba(255,159,64,0.15);  color: var(--orange); }
.badge.n { background: rgba(107,114,148,0.15); color: var(--muted); }
.badge.j { background: rgba(76,159,255,0.15);  color: var(--accent); }

.section-label { display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 12px; }

.insight-box        { border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; border-left: 3px solid; }
.insight-box.good   { background: rgba(0,196,154,0.08);  border-color: var(--green); }
.insight-box.warn   { background: rgba(255,159,64,0.08); border-color: var(--orange); }
.insight-box.danger { background: rgba(255,76,97,0.08);  border-color: var(--red); }
.insight-box.info   { background: rgba(76,159,255,0.08); border-color: var(--accent); }
.insight-title { font-size: 0.78rem; font-weight: 600; margin-bottom: 4px; }
.insight-text  { font-size: 0.75rem; color: var(--muted); line-height: 1.5; }

.filter-bar  { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.filter-chip { display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 14px; background: rgba(76,159,255,0.12); border: 1px solid rgba(76,159,255,0.3); font-size: 0.75rem; color: var(--accent); cursor: pointer; }
.filter-chip:hover { background: rgba(76,159,255,0.2); }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
@media (max-width: 900px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } }

.apr-s { background: rgba(76,159,255,0.12); color: #4C9FFF; }
.may-s { background: rgba(0,196,154,0.12);  color: #00C49A; }
.jun-s { background: rgba(255,159,64,0.12); color: #FF9F40; }
```

---

### `frontend/src/utils/chartConfig.js`

```js
export const COLORS = {
  apr: { solid: '#4C9FFF', alpha: 'rgba(76,159,255,0.6)',  soft: 'rgba(76,159,255,0.15)' },
  may: { solid: '#00C49A', alpha: 'rgba(0,196,154,0.6)',   soft: 'rgba(0,196,154,0.15)'  },
  jun: { solid: '#FF9F40', alpha: 'rgba(255,159,64,0.6)',  soft: 'rgba(255,159,64,0.15)' },
  jul: { solid: '#B57BFF', alpha: 'rgba(181,123,255,0.6)', soft: 'rgba(181,123,255,0.15)'},
  aug: { solid: '#FF4C61', alpha: 'rgba(255,76,97,0.6)',   soft: 'rgba(255,76,97,0.15)'  },
  sep: { solid: '#26C6DA', alpha: 'rgba(38,198,218,0.6)',  soft: 'rgba(38,198,218,0.15)' },
  oct: { solid: '#FFD166', alpha: 'rgba(255,209,102,0.6)', soft: 'rgba(255,209,102,0.15)'},
  nov: { solid: '#7CB9E8', alpha: 'rgba(124,185,232,0.6)', soft: 'rgba(124,185,232,0.15)'},
  dec: { solid: '#98D8C8', alpha: 'rgba(152,216,200,0.6)', soft: 'rgba(152,216,200,0.15)'},
  jan: { solid: '#F5CBA7', alpha: 'rgba(245,203,167,0.6)', soft: 'rgba(245,203,167,0.15)'},
  feb: { solid: '#D7BDE2', alpha: 'rgba(215,189,226,0.6)', soft: 'rgba(215,189,226,0.15)'},
  mar: { solid: '#A9CCE3', alpha: 'rgba(169,204,227,0.6)', soft: 'rgba(169,204,227,0.15)'},
  danger:  { solid: '#FF4C61', alpha: 'rgba(255,76,97,0.6)',   soft: 'rgba(255,76,97,0.15)'  },
  good:    { solid: '#00C49A', alpha: 'rgba(0,196,154,0.6)',   soft: 'rgba(0,196,154,0.15)'  },
  warn:    { solid: '#FF9F40', alpha: 'rgba(255,159,64,0.6)',  soft: 'rgba(255,159,64,0.15)' },
  neutral: { solid: '#6b7294', alpha: 'rgba(107,114,148,0.6)', soft: 'rgba(107,114,148,0.15)'},
}

export const PALETTE = [
  '#4C9FFF','#00C49A','#FF9F40','#B57BFF',
  '#FF4C61','#26C6DA','#FFD166','#7CB9E8',
  '#98D8C8','#F5CBA7','#D7BDE2','#A9CCE3',
]

export function monthColor(key) {
  return COLORS[key] || COLORS.neutral
}

export function baseOptions(overrides = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend:  { labels: { color: '#6b7294', font: { size: 11 } } },
      tooltip: { backgroundColor: '#111320', titleColor: '#e8eaf6', bodyColor: '#a0a4c0', borderColor: '#1e2340', borderWidth: 1 },
    },
    scales: {
      x: { ticks: { color: '#6b7294', font: { size: 11 } }, grid: { color: 'rgba(30,35,64,0.5)' } },
      y: { ticks: { color: '#6b7294', font: { size: 11 } }, grid: { color: 'rgba(30,35,64,0.5)' } },
    },
    ...overrides,
  }
}

export function baseOptionsNoScale(overrides = {}) {
  const opts = baseOptions(overrides)
  delete opts.scales
  return opts
}
```

### `frontend/src/utils/monthConfig.js`

```js
export const MONTH_CONFIG = {
  jan: { label: 'January',   short: 'Jan', cls: 'jan', color: 'var(--jan)', sectionCls: 'jan-s', prev: null,  monthNum: 1  },
  feb: { label: 'February',  short: 'Feb', cls: 'feb', color: 'var(--feb)', sectionCls: 'feb-s', prev: 'jan', monthNum: 2  },
  mar: { label: 'March',     short: 'Mar', cls: 'mar', color: 'var(--mar)', sectionCls: 'mar-s', prev: 'feb', monthNum: 3  },
  apr: { label: 'April',     short: 'Apr', cls: 'apr', color: 'var(--apr)', sectionCls: 'apr-s', prev: 'mar', monthNum: 4  },
  may: { label: 'May',       short: 'May', cls: 'may', color: 'var(--may)', sectionCls: 'may-s', prev: 'apr', monthNum: 5  },
  jun: { label: 'June',      short: 'Jun', cls: 'jun', color: 'var(--jun)', sectionCls: 'jun-s', prev: 'may', monthNum: 6  },
  jul: { label: 'July',      short: 'Jul', cls: 'jul', color: 'var(--jul)', sectionCls: 'jun-s', prev: 'jun', monthNum: 7  },
  aug: { label: 'August',    short: 'Aug', cls: 'aug', color: 'var(--aug)', sectionCls: 'aug-s', prev: 'jul', monthNum: 8  },
  sep: { label: 'September', short: 'Sep', cls: 'sep', color: 'var(--sep)', sectionCls: 'sep-s', prev: 'aug', monthNum: 9  },
  oct: { label: 'October',   short: 'Oct', cls: 'oct', color: 'var(--oct)', sectionCls: 'oct-s', prev: 'sep', monthNum: 10 },
  nov: { label: 'November',  short: 'Nov', cls: 'nov', color: 'var(--nov)', sectionCls: 'nov-s', prev: 'oct', monthNum: 11 },
  dec: { label: 'December',  short: 'Dec', cls: 'dec', color: 'var(--dec)', sectionCls: 'dec-s', prev: 'nov', monthNum: 12 },
}

export const MONTH_KEYS = Object.keys(MONTH_CONFIG)

export function calcChange(curr, prev) {
  if (!curr || !prev) return null
  return ((curr - prev) / prev) * 100
}

export function fmtChange(change) {
  if (change === null) return ''
  return change >= 0 ? `▲ +${change.toFixed(1)}%` : `▼ ${change.toFixed(1)}%`
}

export function changeDir(change) {
  if (change === null) return 'na'
  return change >= 0 ? 'up' : 'dn'
}

export const DELEGATE_COLS = [
  { key: 'name',          label: 'Delegate'    },
  { key: 'territory',     label: 'Territory'   },
  { key: 'total_calls',   label: 'Total Calls' },
  { key: 'prescriber',    label: 'Prescribers' },
  { key: 'pharmacy',      label: 'Pharmacy'    },
  { key: 'drs_converted', label: 'DRs Conv.'   },
  { key: 'days_worked',   label: 'Days'        },
  { key: 'avg_per_day',   label: 'Avg/Day'     },
  { key: 'orders_eur',    label: 'Orders (EUR)'},
  { key: 'ctc_eur',       label: 'CTC (EUR)'   },
  { key: 'ctc_ratio',     label: 'CTC Ratio'   },
]
```

---

### `frontend/src/context/FilterContext.jsx`

```jsx
import { createContext, useContext, useState, useEffect } from 'react'

const FilterContext = createContext(null)

export function FilterProvider({ children, availableMonths }) {
  const [selectedMonths, setSelectedMonths] = useState(null)

  useEffect(() => { setSelectedMonths(null) }, [availableMonths])

  const activeMonths = selectedMonths === null
    ? availableMonths
    : availableMonths.filter(m => selectedMonths.has(m))

  function toggleMonth(month) {
    setSelectedMonths(prev => {
      const next = new Set(prev || availableMonths)
      next.has(month) ? next.delete(month) : next.add(month)
      if (next.size === 0 || next.size === availableMonths.length) return null
      return next
    })
  }

  function setPreset(months) {
    const valid = months.filter(m => availableMonths.includes(m))
    if (valid.length === 0 || valid.length === availableMonths.length) {
      setSelectedMonths(null)
    } else {
      setSelectedMonths(new Set(valid))
    }
  }

  function clearFilter() { setSelectedMonths(null) }

  function isMonthSelected(month) {
    return selectedMonths === null || selectedMonths.has(month)
  }

  return (
    <FilterContext.Provider value={{
      selectedMonths, activeMonths, isFiltered: selectedMonths !== null,
      toggleMonth, setPreset, clearFilter, isMonthSelected,
    }}>
      {children}
    </FilterContext.Provider>
  )
}

export function useFilter() {
  return useContext(FilterContext)
}
```

### `frontend/src/hooks/useDashboard.js`

```js
import axios from 'axios'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

const BASE = import.meta.env.VITE_API_URL || '/api'
const get  = url => axios.get(BASE + url).then(r => r.data)
const post = url => axios.post(BASE + url).then(r => r.data)

export const useAvailableMonths = () =>
  useQuery({ queryKey: ['health'], queryFn: () => get('/health'), staleTime: 60000,
    select: d => d.months_loaded || [] })

export const useOverview   = () => useQuery({ queryKey: ['overview'],   queryFn: () => get('/overview')   })
export const useProducts   = () => useQuery({ queryKey: ['products'],   queryFn: () => get('/products')   })
export const useDelegates  = () => useQuery({ queryKey: ['delegates'],  queryFn: () => get('/delegates')  })
export const useExpenses   = () => useQuery({ queryKey: ['expenses'],   queryFn: () => get('/expenses')   })
export const useActivities = () => useQuery({ queryKey: ['activities'], queryFn: () => get('/activities') })
export const useInsights   = () => useQuery({ queryKey: ['insights'],   queryFn: () => get('/insights')   })
export const useMonth      = m  => useQuery({ queryKey: ['month', m],   queryFn: () => get(`/months/${m}`), enabled: !!m })

export function useRefreshData() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => post('/data/refresh'),
    onSuccess:  () => qc.invalidateQueries(),
  })
}

export function useRefreshInsights() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => post('/insights/refresh'),
    onSuccess: d => qc.setQueryData(['insights'], d),
  })
}
```

---

### `frontend/src/components/KpiCard.jsx`

```jsx
export default function KpiCard({ label, value, sub, change, changeDir, monthColor }) {
  return (
    <div className="kpi-card" style={monthColor ? { borderTop: `2px solid ${monthColor}` } : {}}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value ?? '—'}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
      {change !== undefined && change !== null && (
        <div className={`kpi-change ${changeDir || ''}`}>{change}</div>
      )}
    </div>
  )
}
```

### `frontend/src/components/ChartCard.jsx`

```jsx
export default function ChartCard({ title, sub, height = 'h300', children, monthColor }) {
  return (
    <div className="chart-card" style={monthColor ? { borderTop: `2px solid ${monthColor}` } : {}}>
      <div className="chart-title">{title}</div>
      {sub && <div className="chart-sub">{sub}</div>}
      <div className={height}>{children}</div>
    </div>
  )
}
```

### `frontend/src/components/Badge.jsx`

```jsx
export default function Badge({ text, variant = 'n' }) {
  return <span className={`badge ${variant}`}>{text}</span>
}
```

### `frontend/src/components/SectionLabel.jsx`

```jsx
export default function SectionLabel({ tag, text, monthColor }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <span className="section-label"
        style={monthColor ? { background: `${monthColor}22`, color: monthColor } : {}}>
        {tag || text}
      </span>
      {tag && text && <span style={{ marginLeft: 10, fontSize: '0.85rem', fontWeight: 600 }}>{text}</span>}
    </div>
  )
}
```

### `frontend/src/components/InsightBox.jsx`

```jsx
export default function InsightBox({ type = 'info', icon, title, text, loading }) {
  if (loading) {
    return (
      <div className="insight-box info" style={{ opacity: 0.5 }}>
        <div className="insight-title">Generating insights...</div>
        <div className="insight-text">Please wait.</div>
      </div>
    )
  }
  return (
    <div className={`insight-box ${type}`}>
      <div className="insight-title">{icon && <span style={{ marginRight: 6 }}>{icon}</span>}{title}</div>
      {text !== title && <div className="insight-text">{text}</div>}
    </div>
  )
}
```

### `frontend/src/components/DataTable.jsx`

```jsx
function fmtCell(key, val) {
  if (val === null || val === undefined) return '—'
  if (key === 'ctc_ratio' && typeof val === 'number') {
    const cls = val > 0.3 ? 'd' : val > 0.2 ? 'w' : 'g'
    return <span className={`badge ${cls}`}>{(val * 100).toFixed(1)}%</span>
  }
  if (key === 'pct_listed' && typeof val === 'number') return `${(val * 100).toFixed(0)}%`
  if (typeof val === 'number') {
    return val % 1 === 0 ? val.toLocaleString() : val.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }
  return String(val)
}

export default function DataTable({ title, badge, borderColor, columns = [], rows = [], totalRow }) {
  return (
    <div className="tbl-card" style={borderColor ? { borderTop: `2px solid ${borderColor}` } : {}}>
      <div className="tbl-header">
        <span className="tbl-title">{title}</span>
        {badge && <span className="badge n">{badge}</span>}
      </div>
      <table>
        <thead>
          <tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>{columns.map(c => <td key={c.key}>{fmtCell(c.key, row[c.key])}</td>)}</tr>
          ))}
          {totalRow && (
            <tr style={{ fontWeight: 600, background: '#0d1025' }}>
              {columns.map(c => <td key={c.key}>{fmtCell(c.key, totalRow[c.key])}</td>)}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
```

### `frontend/src/components/TabBar.jsx`

```jsx
import { MONTH_CONFIG } from '../utils/monthConfig.js'

export default function TabBar({ activeTab, onTabChange, availableMonths }) {
  const monthTabs = (availableMonths || []).map(key => ({
    key,
    label: MONTH_CONFIG[key]?.short || key.toUpperCase(),
  }))

  const tabs = [
    { key: 'ov',   label: 'Overview'   },
    ...monthTabs,
    { key: 'prod', label: 'Products'   },
    { key: 'del',  label: 'Delegates'  },
    { key: 'exp',  label: 'Expenses'   },
    { key: 'act',  label: 'Activities' },
    { key: 'nom',  label: 'Team'       },
  ]

  return (
    <div className="tab-bar">
      {tabs.map(t => (
        <button
          key={t.key}
          className={`tab-btn ${activeTab === t.key ? 'active' : ''}`}
          onClick={() => onTabChange(t.key)}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}
```

### `frontend/src/components/FilterBar.jsx`

```jsx
import { useFilter } from '../context/FilterContext.jsx'
import { MONTH_CONFIG } from '../utils/monthConfig.js'

export default function FilterBar({ availableMonths = [] }) {
  const { isFiltered, toggleMonth, clearFilter, isMonthSelected } = useFilter()
  return (
    <div className="filter-bar">
      <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Filter:</span>
      {availableMonths.map(m => {
        const cfg = MONTH_CONFIG[m] || {}
        return (
          <button key={m} onClick={() => toggleMonth(m)} className="filter-chip"
            style={!isMonthSelected(m) ? { opacity: 0.4 } : {}}>
            {cfg.short || m.toUpperCase()}
          </button>
        )
      })}
      {isFiltered && (
        <button onClick={clearFilter} className="filter-chip" style={{ color: 'var(--muted)' }}>
          Clear
        </button>
      )}
    </div>
  )
}
```

### `frontend/src/components/SalesOutcomeCell.jsx`

```jsx
export default function SalesOutcomeCell({ items = [] }) {
  if (!items?.length) return <span style={{ color: 'var(--muted)' }}>—</span>
  return (
    <div>
      {items.map((it, i) => (
        <div key={i} style={{ fontSize: '0.75rem', lineHeight: 1.6 }}>
          {it.product_name} × {it.qty}
          {it.eur_value > 0 && <span style={{ color: 'var(--muted)' }}> (€{it.eur_value.toFixed(0)})</span>}
        </div>
      ))}
    </div>
  )
}
```

### `frontend/src/components/TourPlanSection.jsx`

Build a section that shows:
1. Summary row: Total / Covered / Uncovered / Coverage %
2. Bar chart (by_delegate — planned vs covered per MR)
3. Doughnut chart (overall coverage %)
4. Per-delegate table with tour entries (date, planned area, actual area, covered badge)

Props: `{ tourPlan, cfg }` where `cfg` is from MONTH_CONFIG.

### `frontend/src/components/VisitTrackerSection.jsx`

Build a section that shows:
1. Toggle: sort by Date or by Doctor
2. Bar chart (total visits per delegate)
3. Per-delegate collapsible table (date, doctor, speciality, clinic)

Props: `{ visitTracker, cfg }`

---

### `frontend/src/tabs/OverviewTab.jsx`

Displays:
- KPI row: Total Sales EUR, Achievement %, Total Visits, DRs Converted
- Month comparison bar chart / table
- Product mix doughnut charts (tablet vs injectable per month)
- All products trend line chart
- AI Insights section with refresh button
- Refresh Data button

Uses: `useOverview()`, `useInsights()`, `useRefreshData()`, `useRefreshInsights()`, `useFilter()`

### `frontend/src/tabs/MonthTab.jsx`

Props: `{ month }` (e.g. "apr")

Displays:
- Month KPI row
- Target vs Achieved bar chart (per product)
- Distributor breakdown bar chart
- Delegate performance table
- Activity Expenses table with SalesOutcomeCell
- TourPlanSection
- VisitTrackerSection

Uses: `useMonth(month)`

### `frontend/src/tabs/ProductsTab.jsx`

Displays:
- Sales trend line chart (all products across months)
- Annual vs YTD bar chart
- Category mix per month
- Products KPI row

Uses: `useProducts()`, `useFilter()`

### `frontend/src/tabs/DelegatesTab.jsx`

Displays:
- Q1 summary KPIs
- Delegate performance table (across all months, filterable)
- Tour coverage bar chart per delegate

Uses: `useDelegates()`, `useFilter()`

### `frontend/src/tabs/ExpensesTab.jsx`

Displays:
- Budget flow bar chart (received vs spent per month)
- Activity type breakdown bar chart
- Per-month expense table with SalesOutcomeCell

Uses: `useExpenses()`, `useFilter()`

### `frontend/src/tabs/ActivitiesTab.jsx`

Displays:
- Overall execution rate KPI
- Matched / Planned-not-done / Unplanned-done tables per month
- Summary KPIs (execution rate, outcome EUR)

Uses: `useActivities()`, `useFilter()`

### `frontend/src/tabs/NomenclatureTab.jsx`

Displays a reference glossary built from name_map.py contents:
- Team roster: MR ID, display name, territory
- Product list: ID, name, category
- Activity types
- Territory zones

Hardcode the values from name_map.py directly in this component (no API call needed).

---

### `frontend/src/App.jsx`

```jsx
import { useState } from 'react'
import { FilterProvider } from './context/FilterContext.jsx'
import { useAvailableMonths } from './hooks/useDashboard.js'
import TabBar     from './components/TabBar.jsx'
import FilterBar  from './components/FilterBar.jsx'

import OverviewTab    from './tabs/OverviewTab.jsx'
import MonthTab       from './tabs/MonthTab.jsx'
import ProductsTab    from './tabs/ProductsTab.jsx'
import DelegatesTab   from './tabs/DelegatesTab.jsx'
import ExpensesTab    from './tabs/ExpensesTab.jsx'
import ActivitiesTab  from './tabs/ActivitiesTab.jsx'
import NomenclatureTab from './tabs/NomenclatureTab.jsx'

const AGGREGATE_TABS = new Set(['ov', 'prod', 'del', 'exp', 'act', 'nom'])

function Dashboard() {
  const { data: availableMonths = [] } = useAvailableMonths()
  const [activeTab, setActiveTab] = useState('ov')

  const staticPanels = {
    ov:   <OverviewTab    />,
    prod: <ProductsTab    />,
    del:  <DelegatesTab   />,
    exp:  <ExpensesTab    />,
    act:  <ActivitiesTab  />,
    nom:  <NomenclatureTab />,
  }

  let panel = staticPanels[activeTab]
  if (!panel && availableMonths.includes(activeTab)) {
    panel = <MonthTab month={activeTab} />
  }

  return (
    <FilterProvider availableMonths={availableMonths}>
      <div className="app-shell">
        <div className="app-header">
          <div>
            <div className="app-title">Uganda Sales Dashboard 2026</div>
            <div className="app-subtitle">Pharma Sales Intelligence · FastAPI + React</div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {availableMonths.map(m => (
              <span key={m} style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)', display: 'inline-block' }} />
            ))}
          </div>
        </div>
        <TabBar activeTab={activeTab} onTabChange={setActiveTab} availableMonths={availableMonths} />
        {AGGREGATE_TABS.has(activeTab) && <FilterBar availableMonths={availableMonths} />}
        {panel || <div style={{ color: 'var(--muted)', padding: 40 }}>Loading...</div>}
      </div>
    </FilterProvider>
  )
}

export default function App() {
  return <Dashboard />
}
```

---

## `start.sh`

```bash
#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Uganda Dashboard 2026..."

pkill -f "uvicorn main:app" 2>/dev/null || true
sleep 1

echo "Starting FastAPI backend on port 8000..."
cd "$SCRIPT_DIR/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
.venv/bin/uvicorn main:app --port 8000 --log-level warning &
BACKEND_PID=$!

echo "Waiting for backend..."
for i in {1..20}; do
  sleep 1
  if curl -s http://localhost:8000/api/health 2>/dev/null | grep -q "ok"; then
    echo "Backend ready."
    break
  fi
done

echo "Starting React frontend..."
cd "$SCRIPT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!
sleep 2

echo ""
echo "Uganda Dashboard 2026"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000/api/health"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" INT TERM
wait
```

---

## Key Differences from IVC Ivory Coast

| Aspect           | IVC (Ivory Coast)              | Uganda                                   |
|------------------|--------------------------------|------------------------------------------|
| Currency         | FCFA (÷ 655.97 → EUR)          | UGX (÷ 3800 → EUR, configurable)         |
| Env var          | `IVC_DATA_PATH`                | `UGANDA_DATA_PATH`                       |
| Data folder      | `IVC/`                         | `UGANDA/`                                |
| name_map style   | Fuzzy matching + auto-registry | Exact dicts only (no rapidfuzz in name_map) |
| Unknown names    | Returns "UNKNOWN"              | Returns raw string as-is                 |
| Starting month   | January                        | April (or wherever your data starts)     |
| Doctor index     | Built from visits at startup   | Passthrough (title-case raw string)      |

---

## Verification Checklist

After building, verify each step:

1. `cd backend && .venv/bin/python -c "from loaders import load_all_data; from storage import get_storage; d = load_all_data(get_storage()); print(list(d.keys()))"` — should print `['apr']`
2. `curl http://localhost:8000/api/health` → `{"status":"ok","months_loaded":["apr"]}`
3. `curl http://localhost:8000/api/overview` → JSON with `q1_summary.total_sales_eur > 0`
4. `curl http://localhost:8000/api/months/apr` → JSON with `kpis`, `product_sales`, `delegate_table`
5. Frontend at `http://localhost:5173` — Overview tab loads with non-zero KPIs
6. Products tab: bar charts have data
7. Delegates tab: table has delegate rows
8. If any tab shows zeros or empty tables, re-read the corresponding Excel file in Step 0 and fix the column name mappings in `loaders.py`

---

## Common Issues and Fixes

**Symptom**: All sales show EUR 0  
**Fix**: Re-read the sales file, find the exact distributor column headers, update every `col(hdr, ...)` call in `load_sales()`

**Symptom**: Delegates tab empty  
**Fix**: Print `xl.sheet_names` in `load_monthly_reports()` and update the `sheets_lower.get(...)` lookup to match the actual tab name

**Symptom**: MR IDs show raw names instead of IDs  
**Fix**: Add the exact delegate names (uppercased, exactly as in the file) to `MR_CANONICAL` in `name_map.py`

**Symptom**: Products show as unknown IDs  
**Fix**: Add exact product names (uppercased) to `PRODUCT_CANONICAL` in `name_map.py`

**Symptom**: Visit Tracker shows 0 visits  
**Fix**: Print the first 10 rows of each sheet to find where doctor names start; update `hdr_row_v` default in `load_visit_tracker()`

**Symptom**: `TOTAL_VALUE_EUR` is 0 but `TOTAL_SALES` is correct  
**Fix**: Rates were not loaded — check that the master sales file name contains "sales" and that `build_canonical_rates()` finds the PRODUCT and RATE columns
