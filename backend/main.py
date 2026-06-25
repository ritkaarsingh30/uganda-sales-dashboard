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

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from storage import get_storage

app_state = {}
_refresh_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from loaders import load_all_data, load_annual_projections, _find_month_file, _discover_month_folders
    storage = get_storage()
    print("[startup] Loading Uganda data files...")
    data = load_all_data(storage)
    app_state["data"]    = data
    app_state["storage"] = storage

    # Annual projections = sum of each month's projection targets across all loaded months
    months = _discover_month_folders(storage)
    combined: dict[str, float] = {}
    for _, folder_name in months:
        pb = _find_month_file(storage, folder_name, "projection")
        if pb:
            for prod, val in load_annual_projections(pb).items():
                combined[prod] = combined.get(prod, 0.0) + val
    app_state["annual_projections"] = combined
    print(f"[startup] Annual projections (summed over {len(months)} months): {len(combined)} products")

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
        from loaders import load_all_data, load_annual_projections, _find_month_file, _discover_month_folders
        from cache.redis_client import flush_all_api_cache
        storage = app_state.get("storage")
        if hasattr(storage, "discover"):
            storage.discover()
        data    = load_all_data(storage)
        app_state["data"]           = data
        app_state["insights_cache"] = None
        months = _discover_month_folders(storage)
        combined: dict[str, float] = {}
        for _, folder_name in months:
            pb = _find_month_file(storage, folder_name, "projection")
            if pb:
                for prod, val in load_annual_projections(pb).items():
                    combined[prod] = combined.get(prod, 0.0) + val
        app_state["annual_projections"] = combined
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
