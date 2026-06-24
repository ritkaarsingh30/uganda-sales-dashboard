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
