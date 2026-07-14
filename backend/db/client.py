"""
Database layer — Supabase if available, in-memory fallback otherwise.

The singleton client is initialised on first access. If Supabase env
vars are missing or the connection fails, all operations silently
degrade to in-memory storage so the bot never crashes.

Every public function wraps its Supabase call in try/except so that
a network error, missing table, or DNS failure never propagates to
the caller — the in-memory fallback is used instead.
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_client = None
_available = False
_fallback: dict = {"saved_items": [], "bio_state": {}, "bot_logs": []}
_save_code_lock = asyncio.Lock()
_initialised = False


def _check_available() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def get_db():
    """Return the Supabase client, or None if unavailable."""
    global _client, _available, _initialised
    if _initialised:
        return _client if _available else None

    _initialised = True

    if not _check_available():
        logger.warning("Supabase env vars not set — using in-memory fallback.")
        _available = False
        return None

    try:
        from supabase import create_client
        _client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
        _available = True
        logger.info("Supabase client initialised.")
        return _client
    except Exception as exc:
        logger.warning("Supabase init failed (%s) — using in-memory fallback.", exc)
        _available = False
        return None


def is_available() -> bool:
    return _available


async def log(owner_id: int, level: str, message: str, context: dict | None = None) -> None:
    try:
        entry = {
            "owner_id": owner_id,
            "level": level,
            "message": message,
            "context": context or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db = get_db()
        if db:
            db.table("bot_logs").insert(entry).execute()
        else:
            entry["id"] = len(_fallback["bot_logs"]) + 1
            _fallback["bot_logs"].append(entry)
    except Exception:
        pass


async def get_next_save_code() -> str:
    async with _save_code_lock:
        db = get_db()
        if db:
            try:
                result = db.table("saved_items").select("id", count="exact").execute()
                count = result.count or 0
            except Exception:
                count = len(_fallback["saved_items"])
        else:
            count = len(_fallback["saved_items"])
        return f"SV-{(count + 1):06d}"


def insert_save(data: dict) -> dict | None:
    db = get_db()
    if db:
        try:
            result = db.table("saved_items").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as exc:
            logger.warning("Supabase insert_save failed (%s) — using fallback.", exc)
    data["id"] = len(_fallback["saved_items"]) + 1
    _fallback["saved_items"].append(data)
    return data


def query_save(save_code: str) -> dict | None:
    db = get_db()
    if db:
        try:
            result = (
                db.table("saved_items")
                .select("*")
                .eq("save_code", save_code.upper())
                .maybe_single()
                .execute()
            )
            return result.data
        except Exception as exc:
            logger.warning("Supabase query_save failed (%s) — using fallback.", exc)
    for item in _fallback["saved_items"]:
        if item.get("save_code", "").upper() == save_code.upper():
            return item
    return None


def list_saves(owner_id: int, limit: int = 50, offset: int = 0) -> tuple[list, int]:
    db = get_db()
    if db:
        try:
            result = (
                db.table("saved_items")
                .select("*")
                .eq("owner_id", owner_id)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            count_res = (
                db.table("saved_items")
                .select("id", count="exact")
                .eq("owner_id", owner_id)
                .execute()
            )
            return result.data or [], count_res.count or 0
        except Exception as exc:
            logger.warning("Supabase list_saves failed (%s) — using fallback.", exc)
    items = [s for s in _fallback["saved_items"] if s.get("owner_id") == owner_id]
    total = len(items)
    return items[offset:offset + limit], total


def count_saves(owner_id: int, save_type: str | None = None) -> int:
    db = get_db()
    if db:
        try:
            q = db.table("saved_items").select("id", count="exact").eq("owner_id", owner_id)
            if save_type:
                q = q.eq("save_type", save_type)
            result = q.execute()
            return result.count or 0
        except Exception as exc:
            logger.warning("Supabase count_saves failed (%s) — using fallback.", exc)
    items = [s for s in _fallback["saved_items"] if s.get("owner_id") == owner_id]
    if save_type:
        items = [s for s in items if s.get("save_type") == save_type]
    return len(items)


def get_bio_state(owner_id: int) -> dict | None:
    db = get_db()
    if db:
        try:
            result = (
                db.table("bio_state")
                .select("*")
                .eq("owner_id", owner_id)
                .maybe_single()
                .execute()
            )
            return result.data
        except Exception as exc:
            logger.warning("Supabase get_bio_state failed (%s) — using fallback.", exc)
    return _fallback["bio_state"].get(owner_id)


def get_or_create_bio_state(owner_id: int) -> dict:
    state = get_bio_state(owner_id)
    if state:
        return state

    default = {
        "owner_id": owner_id,
        "template": "🕒 {time} | 💭 {mood}",
        "mood": "😊",
        "custom_text": "",
        "is_active": False,
        "last_bio": "",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    db = get_db()
    if db:
        try:
            db.table("bio_state").insert(default).execute()
            result = (
                db.table("bio_state")
                .select("*")
                .eq("owner_id", owner_id)
                .maybe_single()
                .execute()
            )
            if result.data:
                return result.data
        except Exception as exc:
            logger.warning("Supabase get_or_create_bio_state failed (%s) — using fallback.", exc)
    _fallback["bio_state"][owner_id] = default
    return default


def update_bio_state(owner_id: int, updates: dict) -> None:
    db = get_db()
    if db:
        try:
            db.table("bio_state").update(updates).eq("owner_id", owner_id).execute()
            return
        except Exception as exc:
            logger.warning("Supabase update_bio_state failed (%s) — using fallback.", exc)
    state = _fallback["bio_state"].get(owner_id, {})
    state.update(updates)
    _fallback["bio_state"][owner_id] = state


def count_logs(owner_id: int) -> int:
    db = get_db()
    if db:
        try:
            result = (
                db.table("bot_logs")
                .select("id", count="exact")
                .eq("owner_id", owner_id)
                .execute()
            )
            return result.count or 0
        except Exception as exc:
            logger.warning("Supabase count_logs failed (%s) — using fallback.", exc)
    return len([l for l in _fallback["bot_logs"] if l.get("owner_id") == owner_id])


def list_logs(owner_id: int, limit: int = 100) -> list:
    db = get_db()
    if db:
        try:
            result = (
                db.table("bot_logs")
                .select("*")
                .eq("owner_id", owner_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            logger.warning("Supabase list_logs failed (%s) — using fallback.", exc)
    logs = [l for l in _fallback["bot_logs"] if l.get("owner_id") == owner_id]
    return logs[-limit:] if limit > 0 else logs


def clean_logs(owner_id: int, days: int = 7) -> int:
    db = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    if db:
        try:
            result = (
                db.table("bot_logs")
                .delete()
                .eq("owner_id", owner_id)
                .lt("created_at", cutoff)
                .execute()
            )
            return len(result.data) if result.data else 0
        except Exception as exc:
            logger.warning("Supabase clean_logs failed (%s) — using fallback.", exc)
    before = len(_fallback["bot_logs"])
    _fallback["bot_logs"] = [
        l for l in _fallback["bot_logs"]
        if l.get("owner_id") != owner_id or l.get("created_at", "") >= cutoff
    ]
    return before - len(_fallback["bot_logs"])
