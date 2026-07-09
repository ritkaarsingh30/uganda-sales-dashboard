# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# Start both backend and frontend together
./start.sh

# Or individually:
# Backend (from backend/)
.venv/bin/uvicorn main:app --port 8000 --reload

# Frontend (from frontend/)
npm run dev -- --host 0.0.0.0 --port 5173
```

URLs: frontend at `http://localhost:5173`, backend at `http://localhost:8000`.

## Backend development

```bash
cd backend

# Install dependencies into the venv
.venv/bin/pip install -r requirements.txt

# Run with auto-reload
.venv/bin/uvicorn main:app --port 8000 --reload
```

Key env vars in `backend/.env`:
- `STORAGE_BACKEND=local` or `sheets` — `local` reads Excel files from `UGANDA_DATA_PATH`; `sheets` reads the same folder/file layout mirrored inside a shared Google Drive folder (requires `GOOGLE_DRIVE_FOLDER_ID` and `GOOGLE_CREDENTIALS_JSON`, a service-account JSON pasted as one line)
- `UGANDA_DATA_PATH=../UGANDA` — path to the Excel data folder (used by `local` backend)
- `GROQ_API_KEY` — required for AI insights (Llama 3.1 via Groq)
- `REDIS_URL` — optional; caching degrades gracefully if Redis is unavailable

## Frontend development

```bash
cd frontend
npm run dev        # dev server
npm run build      # production build to dist/
```

Set `VITE_API_URL` to override the default `/api` base URL (useful when running frontend and backend on different origins).

## Architecture

### Data flow
Excel files in `UGANDA/` → `loaders.py` (pandas parsing) → `app_state` dict in memory → FastAPI routers → React frontend via TanStack Query.

Data is loaded once at startup (`lifespan`) and cached in `app_state["data"]`. The `POST /api/data/refresh` endpoint reloads from disk and flushes Redis cache.

### Excel file layout (`UGANDA/`)
The root `UGANDA/` folder holds master files (e.g. `UGANDA SALE APRIL 26.xlsx`). Month subfolders (e.g. `UGANDA/April/`) contain per-month files:
- Sales file (`*sale*`)
- Projection file (`*projection*`)
- Expenses file (`*expense*`)
- Visit tracker file (`*visit*`)
- Monthly report file (`*monthly*` or `*report*`)
- Tour plan file (`*tour*`)

`loaders.py` discovers these by folder name (matches `MONTH_FOLDER_MAP`) and file keyword matching.

The Sheets backend (`STORAGE_BACKEND=sheets`) mirrors this same root + month-subfolder convention inside one shared Google Drive folder — native Google Sheets are exported to XLSX on read, uploaded `.xlsx` files are downloaded as-is, so `loaders.py` is unchanged either way. If a folder has both a native Google Sheet and an uploaded `.xlsx` copy with the same base name, the native Sheet always wins (it's assumed to be the one people actively edit). Note: canonical sales-rate pre-seeding (`build_canonical_rates`) only runs off a root-level "sales" file; since the Drive folder currently has no loose root files (only month subfolders), this is a no-op under Sheets mode and each month falls back to its own per-row rates.

### Backend structure
- `main.py` — FastAPI app, lifespan loader, CORS, NaN-safe JSON response class
- `loaders.py` — all Excel parsing; produces DataFrames stored in `app_state["data"]`
- `routers/` — one router per tab: `overview`, `months`, `products`, `delegates`, `expenses`, `insights`, `activities`
- `name_map.py` — normalization/display names for MRs, products, activities, territories
- `constants.py` — `UGX_TO_EUR = 3800.0`, color palette
- `storage/` — `StorageBackend` ABC + `local.py` (Excel filesystem) and `sheets.py` (Google Drive) implementations; `get_storage()` factory reads `STORAGE_BACKEND` env var
- `cache/redis_client.py` — optional Redis caching layer for API responses
- `insights_builder.py` — builds the prompt and calls Groq to generate action-point insights

### Frontend structure
- `src/App.jsx` — top-level routing between tabs; `AGGREGATE_TABS` use `FilterBar`, month tabs render `<MonthTab month={key} />`
- `src/hooks/useDashboard.js` — all TanStack Query hooks; single source of truth for API calls
- `src/context/FilterContext.jsx` — multi-month filter state shared across aggregate tabs (`null` = all months selected)
- `src/tabs/` — one component per dashboard tab
- `src/components/` — shared UI: `KpiCard`, `ChartCard`, `DataTable`, `FilterBar`, `TabBar`, `Badge`, etc.
- `src/utils/chartConfig.js` — Chart.js base options and per-month color palette; `src/utils/monthConfig.js` — month metadata

### Key conventions
- Currency: sales values are in EUR; budget fields in the Excel are UGX and converted using `UGX_TO_EUR`.
- NaN/Infinity in API responses are serialized as `null` by `NaNSafeJSONResponse`.
- Product normalization uses `rapidfuzz` fuzzy matching in `name_map.py` to handle inconsistent Excel spellings.
- All tab data queries pass `months` as a query param array when the global filter is active.
