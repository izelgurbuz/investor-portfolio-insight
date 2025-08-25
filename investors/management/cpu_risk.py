from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from math import sqrt
from random import gauss
from typing import Dict, List, Optional


@dataclass
class Position:
    weight: float  # shares
    price: float
    volatility: float


# paths = days
def simulate_portfolio_pnl(
    positions: List[Position], paths: int = 50_000
) -> List[float]:
    pnls = []
    for _ in range(paths):
        pnl = 0.0
        for position in positions:
            daily_sigma = position.volatility / sqrt(252)
            r = gauss(0.0, daily_sigma)
            pnl += r * position.weight * position.price
        pnls.append(pnl)
    return pnls


def value_at_risk(pnls, alpha=0.95) -> int:
    if not pnls:
        return 0
    sorted_pnls = sorted(pnls)
    idx = max(0, int((1 - alpha) * len(sorted_pnls)) - 1)
    return -sorted_pnls[idx]


def task(positions, paths, alpha=0.95):
    pnls = simulate_portfolio_pnl(positions, paths=paths)
    return value_at_risk(pnls, alpha)


def portfolio_var_parallel(
    portfolios_inputs: Dict[int, List[Position]],
    paths: int = 50_000,
    max_workers: Optional[int] = None,
) -> Dict[int, float]:
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            idx: pool.submit(task, positions, paths)
            for idx, positions in portfolios_inputs.items()
        }

    return {idx: value.result() for idx, value in futures.items()}
