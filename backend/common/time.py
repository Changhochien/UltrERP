"""Time provider — injectable clock for business logic.

In production, returns real wall-clock time.
In dev/stories, a CURRENT_DATE env var pins "today" to a fixed value.
If CURRENT_DATE is unset, the latest demand date is auto-detected from
stock_adjustment + raw_legacy.tbsslipx so the ROP calculator
always uses the most recent data in the system.

The cached date is refreshed once per day automatically.
"""

from __future__ import annotations

import asyncio
import os
import time as _time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Lock, Thread

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from common.config import settings


_bg_loop: asyncio.AbstractEventLoop | None = None
_bg_loop_lock: asyncio.Lock | None = None
_bg_result: date | None = None
_bg_exc: BaseException | None = None
_bg_ready = False
_bg_cache_time: float = 0
_CACHE_TTL_SECONDS = 86400  # 24 hours


def _start_bg_loop() -> None:
    """Start a background thread with an async event loop for DB queries."""
    global _bg_loop, _bg_loop_lock

    def target():
        global _bg_loop, _bg_loop_lock
        _bg_loop = asyncio.new_event_loop()
        _bg_loop_lock = asyncio.Lock()
        asyncio.set_event_loop(_bg_loop)
        _bg_loop.run_forever()

    t = Thread(target=target, daemon=True)
    t.start()

    for _ in range(50):
        if _bg_loop is not None and _bg_loop.is_running():
            break
        _time.sleep(0.05)


def _query_bg_loop() -> date:
    """Run the date-detection query in the background loop, return result."""
    global _bg_loop, _bg_result, _bg_exc, _bg_ready, _bg_cache_time

    if _bg_loop is None:
        _start_bg_loop()
        for _ in range(50):
            if _bg_loop is not None and _bg_loop.is_running():
                break
            _time.sleep(0.05)

    # Check cache TTL
    now = _time.monotonic()
    if _bg_result is not None and (now - _bg_cache_time) < _CACHE_TTL_SECONDS:
        return _bg_result

    _bg_ready = False
    _bg_exc = None

    async def _query() -> None:
        global _bg_result, _bg_exc, _bg_cache_time, _bg_ready
        try:
            db_url = getattr(settings, "database_url", None)
            if db_url is None:
                _bg_result = date.today()
                return
            engine = create_async_engine(db_url, pool_size=1, max_overflow=0)
            Session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            async with Session() as s:
                r1 = await s.execute(text(
                    "SELECT MAX(created_at) FROM public.stock_adjustment WHERE actor_id = 'backfill-script'"
                ))
                r2 = await s.execute(
                    text("SELECT MAX(col_3) FROM raw_legacy.tbsslipx WHERE col_3 IS NOT NULL AND col_3 != ''")
                )
                stock_max = r1.scalar()
                legacy_raw = r2.scalar()

                candidates: list[date] = []
                if stock_max:
                    if isinstance(stock_max, datetime):
                        candidates.append(stock_max.date())
                    elif isinstance(stock_max, date):
                        candidates.append(stock_max)
                if legacy_raw:
                    d = datetime.strptime(str(legacy_raw), "%Y-%m-%d").date()
                    candidates.append(d)

                if candidates:
                    _bg_result = max(candidates)
                else:
                    _bg_result = date.today()
                _bg_cache_time = _time.monotonic()
        except Exception as exc:
            _bg_exc = exc
            _bg_result = date.today()
        finally:
            _bg_ready = True

    future = asyncio.run_coroutine_threadsafe(_query(), _bg_loop)
    future.result(timeout=10)
    if _bg_exc:
        raise _bg_exc
    return _bg_result or date.today()


def _get_fallback_date() -> date:
    """Return the effective 'today' for business logic.

    Priority:
      1. CURRENT_DATE env var (explicit override — never cached)
      2. Latest demand date found in stock_adjustment or tbsslipdto (cached 24h)
      3. Real date.today() as final fallback
    """
    # Explicit override — always fresh
    raw = os.environ.get("CURRENT_DATE") or getattr(settings, "current_date", None)
    if raw:
        return datetime.strptime(raw, "%Y-%m-%d").date()

    # Auto-detect, cached for 24h
    try:
        return _query_bg_loop()
    except Exception:
        pass

    return date.today()


def utc_now() -> datetime:
    """Return current UTC datetime, using the effective fallback date."""
    fallback = _get_fallback_date()
    today_real = date.today()
    if fallback < today_real:
        return datetime(fallback.year, fallback.month, fallback.day, tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def today() -> date:
    """Return the effective today's date for business logic."""
    return _get_fallback_date()
