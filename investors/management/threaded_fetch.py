import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, Optional, Tuple

import requests

from investors.management.utils.parser_and_financial_computations import (
    demo_quote,
    parse_yahoo_chart_payload,
)
from investors.management.utils.types_and_enums import Source

YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval=1d"
)
ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"

ALPHAVANTAGE_API_KEY = "WTU2S8XTKLIY589G"


def _fake_network_fetch(asset_id: int, ticker: str) -> Tuple[int, float, float]:
    time.sleep(0.1 + hash(ticker) % 300 / 1000.0)
    price, vol = demo_quote(ticker)
    return asset_id, price, vol


def _alpha_vantage_fetch(asset_id: int, ticker: str) -> Tuple[int, float, float]:
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": ticker,
        "apikey": ALPHAVANTAGE_API_KEY,
    }

    with requests.get(ALPHAVANTAGE_URL, params=params, timeout=10) as res:
        data = res.json()

    price_str = data.get("Global Quote", {}).get("05. price")
    if not price_str:
        price, vol = demo_quote(ticker)
        return asset_id, price, vol
    price = float(price_str)
    vol = 0.20
    return asset_id, price, vol


def _yahoo_fetch(asset_id: int, name: str) -> Optional[Tuple[float, float, float]]:
    url = YAHOO_CHART_URL.format(symbol=name)
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    payload = r.json()
    parsed = parse_yahoo_chart_payload(payload)
    price, vol = parsed
    return asset_id, price, vol


def fetch_quotes_threaded(
    assets: Iterable[tuple[int, str]],
    source: Source = "demo",
    max_workers: int = 50,
) -> dict[int, tuple[float, float]]:
    result: dict[int, tuple[float, float]] = {}
    fn = None
    if source == "demo":
        fn = _fake_network_fetch
    if source == "alphavantage":
        fn = _alpha_vantage_fetch
    if source == "yahoo":
        fn = _yahoo_fetch

    # free-tier: keep workers small to respect rate limits
    max_workers = min(max_workers, 5)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = [pool.submit(fn, aid, tkr) for aid, tkr in assets]
        for fut in as_completed(futs):
            aid, price, vol = fut.result()
            result[aid] = (price, vol)
    return result
