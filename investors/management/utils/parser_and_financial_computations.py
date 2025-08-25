import math
import statistics
from typing import List, Optional, Tuple


def annualized_volatility_from_closes(closes: List[float]) -> Optional[float]:
    """Compute annualized volatility from daily closes using log returns."""
    # Need at least 3 points to produce 2 returns & stdev
    series = [float(c) for c in closes if c is not None]
    if len(series) < 3:
        return None
    rets = []
    for i in range(1, len(series)):
        p0, p1 = series[i - 1], series[i]
        if p0 and p1 and p0 > 0 and p1 > 0:
            rets.append(math.log(p1 / p0))
    if len(rets) < 2:
        return None
    daily_sigma = statistics.stdev(rets)
    return float(daily_sigma * math.sqrt(252.0))


def parse_yahoo_chart_payload(payload: dict) -> Optional[Tuple[float, float]]:
    """Extract (price, vol) from Yahoo chart JSON payload."""
    try:
        result = payload["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        # price: last non-None close
        price = next((float(c) for c in reversed(closes) if c is not None), None)
        if price is None:
            return None
        vol = annualized_volatility_from_closes(closes)
        if vol is None:
            # Fallback: zero volatility if we truly cannot compute; acceptable for missing history
            vol = 0.0
        return float(price), float(vol)
    except Exception:
        return None


def demo_quote(ticker: str) -> Tuple[float, float]:
    base = (sum(ord(c) for c in ticker) % 25) + 5  # 5..29
    price = float(20 + base * 18)  # 20..542
    vol = 0.12 + (len(ticker) % 7) * 0.03  # 0.12..0.30
    return price, vol
