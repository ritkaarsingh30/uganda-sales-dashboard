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
            if line.upper().startswith(f"[{tag}]"):
                t = val
                line = line[len(tag) + 2:].strip()
                break
        # Split "TITLE | body text" if separator present
        if " | " in line:
            title_part, body_part = line.split(" | ", 1)
        else:
            title_part = line[:60]
            body_part  = line
        results.append({"type": t, "icon": icon_map[t], "title": title_part.strip(), "text": body_part.strip()})
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


@router.get("/insights/delegates")
async def get_delegate_insights():
    cached = await get_api_cache("insights:delegates")
    if cached:
        return cached
    data = app_state.get("data", {})
    from insights_builder import generate_delegate_insights
    text   = await generate_delegate_insights(data)
    result = {"insights": _parse_insights(text), "cached": False}
    await set_api_cache("insights:delegates", result, ttl=7200)
    return result


@router.post("/insights/delegates/refresh")
async def refresh_delegate_insights():
    from cache.redis_client import invalidate_api_keys
    await invalidate_api_keys(["insights:delegates"])
    data   = app_state.get("data", {})
    from insights_builder import generate_delegate_insights
    text   = await generate_delegate_insights(data)
    result = {"insights": _parse_insights(text), "cached": False}
    await set_api_cache("insights:delegates", result, ttl=7200)
    return result


@router.get("/insights/activities")
async def get_activity_insights():
    cached = await get_api_cache("insights:activities")
    if cached:
        return cached
    data = app_state.get("data", {})
    from insights_builder import generate_activity_insights
    text   = await generate_activity_insights(data)
    result = {"insights": _parse_insights(text), "cached": False}
    await set_api_cache("insights:activities", result, ttl=7200)
    return result


@router.post("/insights/activities/refresh")
async def refresh_activity_insights():
    from cache.redis_client import invalidate_api_keys
    await invalidate_api_keys(["insights:activities"])
    data   = app_state.get("data", {})
    from insights_builder import generate_activity_insights
    text   = await generate_activity_insights(data)
    result = {"insights": _parse_insights(text), "cached": False}
    await set_api_cache("insights:activities", result, ttl=7200)
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
