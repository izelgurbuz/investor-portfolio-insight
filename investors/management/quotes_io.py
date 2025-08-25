from __future__ import annotations

import asyncio
import json
import random
from typing import Dict, Iterable, List, Optional, Tuple

from investors.management.utils.parser_and_financial_computations import (
    demo_quote,
    parse_yahoo_chart_payload,
)
from investors.management.utils.types_and_enums import Source

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import requests
except ImportError:
    requests = None

YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval=1d"
)

ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"
ALPHAVANTAGE_API_KEY = "WTU2S8XTKLIY589G"


async def _fake_network_fetch(asset_id: int, ticker: str) -> Tuple[int, float, float]:
    await asyncio.sleep(0.1 + hash(ticker) % 300 / 1000.0)
    price, vol = demo_quote(ticker)
    return asset_id, price, vol


async def _alpha_vantage_fetch(
    session, api_key, asset_id, ticker
) -> Tuple[int, float, float]:
    params = {"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": api_key}

    async with session.get(ALPHAVANTAGE_URL, params=params, timeout=10) as res:
        data = await res.json()

    price_str = data.get("Global Quote", {}).get("05. price")
    if not price_str:
        price, vol = demo_quote(ticker)
        return asset_id, price, vol
    price = float(price_str)
    vol = 0.20

    return asset_id, price, vol


# Backoff
async def _sleep_with_jitter(base_delay: float, attempt: int, cap: float) -> None:
    # Exponential backoff with full jitter
    raw = min(cap, base_delay * (2**attempt))
    # jitter -> to desynchronize clients
    delay = raw * random.uniform(0.5, 1.5)
    await asyncio.sleep(delay)


def _parse_retry_after(seconds_or_date: str) -> Optional[float]:
    # If Yahoo sends it ..
    try:
        return float(seconds_or_date)
    except Exception:
        return None


async def _yahoo_fetch(
    session,
    asset_id,
    symbol,
    max_retries: int = 4,
    base_delay: float = 0.4,
    cap_delay: float = 6.0,  # an upper bound so the wait doesn’t explode forever
) -> Optional[Tuple[int, float, float]]:
    url = YAHOO_CHART_URL.format(symbol=symbol)

    attempt = 0
    while True:
        try:
            async with session.get(url) as resp:
                # 429: too many requests
                if resp.status == 429:
                    ra = resp.headers.get("Retry-After")
                    wait = _parse_retry_after(ra) if ra else None
                    if wait is None:
                        # fall back to jittered backoff
                        if attempt >= max_retries:
                            print("Out of attempts!")
                            return None
                        await _sleep_with_jitter(base_delay, attempt, cap_delay)
                        attempt += 1
                        continue
                    else:
                        await asyncio.sleep(wait)
                        # do not increment attempt if provider guided us
                        continue

                # 5xx: transient server errors
                if 500 <= resp.status < 600:
                    if attempt >= max_retries:
                        return None
                    await _sleep_with_jitter(base_delay, attempt, cap_delay)
                    attempt += 1
                    continue

                # Other 4xx raise for non retriable client errors
                resp.raise_for_status()
                payload = await resp.json(loads=json.loads)
                parsed = parse_yahoo_chart_payload(payload)
                if parsed is None:
                    return None
                price, vol = parsed
                return asset_id, price, vol
        except (
            aiohttp.ClientConnectionError,
            aiohttp.ServerTimeoutError,
            asyncio.TimeoutError,
        ):
            if attempt >= max_retries:
                return None
            await _sleep_with_jitter(base_delay, attempt, cap_delay)
            attempt += 1
            continue
        except aiohttp.ClientError:
            # Non-retriable client errors (4xx other than 429)
            return None


async def fetch_quotes_async(
    ids_and_names: Iterable[Tuple[int, str]],
    source: Source = "demo",
    concurrency: int = 50,
    total_timeout_sec: float = 30.0,
    connector_limit: int = 100,
) -> Dict[int, Tuple[float, float]]:
    result: Dict[int, Tuple[float, float]] = {}

    sem = asyncio.Semaphore(concurrency)
    timeout = aiohttp.ClientTimeout(total=total_timeout_sec)
    connector = aiohttp.TCPConnector(limit=connector_limit, enable_cleanup_closed=True)

    if source == "demo":

        async def bounded_demo(aid: int, tkr: str):
            async with sem:
                asset_id, price, vol = await _fake_network_fetch(aid, tkr)
                result[asset_id] = (price, vol)

        tasks: List[asyncio.Task] = [
            asyncio.create_task(bounded_demo(a_id, ticker))
            for a_id, ticker in ids_and_names
        ]
        await asyncio.gather(*tasks)
        return result

    if aiohttp is None:
        raise RuntimeError("aiohttp not installed. Run: pip install aiohttp")

    concurrency = min(concurrency, 5)
    sem = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:

        async def bounded_real(
            aid: int, symbol: str
        ) -> Optional[Tuple[int, Tuple[float, float]]]:
            async with sem:
                data = (
                    await _yahoo_fetch(session, aid, symbol)
                    if source == "yahoo"
                    else await _alpha_vantage_fetch(
                        session, ALPHAVANTAGE_API_KEY, aid, symbol
                    )
                )
                if data:
                    asset_id, price, vol = data
                    result[asset_id] = (price, vol)

        tasks = [bounded_real(aid, name) for aid, name in ids_and_names]
        await asyncio.gather(*tasks, return_exceptions=False)

    return result
