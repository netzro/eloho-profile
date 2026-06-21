from datetime import datetime
from loguru import logger
from eloho.config import MONTHLY_BUDGET, STOCK_WEIGHTS, STOCKS, TARGET_UNITS, LIMIT_GUARD_PCT
from eloho.db import save_dca_round, get_last_round
from eloho.prices import get_prices

MIN_BUY_COST = 5_000  # Minimum NGN cost per stock per round (fixed)


def _get_holdings(round_data: dict | None = None) -> dict[str, int]:
    """Get current units held per ticker.

    Args:
        round_data: Pre-fetched round data. If None, fetches from DB.
    """
    if round_data is None:
        round_data = get_last_round()
    holdings = {}
    if round_data and round_data.get("allocations"):
        for a in round_data["allocations"]:
            ticker = a["ticker"]
            units = a.get("units") or 0
            holdings[ticker] = holdings.get(ticker, 0) + int(units)
    return holdings


def _compute_limit_price(price: float) -> float:
    """Compute limit price based on LIMIT_GUARD_PCT."""
    multiplier = 1 - (LIMIT_GUARD_PCT / 100)
    return round(price * multiplier, 2)


def _min_units_for_cost(price: float, min_cost: float) -> int:
    """Calculate minimum whole units needed to meet the min cost threshold."""
    if price <= 0:
        return 0
    return int(min_cost // price) + (1 if min_cost % price != 0 else 0)


def compute_allocations(
    prices: dict,
    budget: float = MONTHLY_BUDGET,
    holdings: dict[str, int] | None = None,
) -> list[dict]:
    """Compute DCA allocation across ALL 7 stocks with priority + min-₦5k rules.

    Args:
        prices: Dict of ticker -> {price, change_pct}
        budget: Total budget for this round
        holdings: Pre-computed holdings. If None, fetches from DB.

    Logic:
    1. Sort stocks by remaining_units ascending (closest to target first)
    2. Each stock must cost at least MIN_BUY_COST to enter
    3. Remaining budget distributed by weight
    4. All 7 stocks always appear in output
    """
    if holdings is None:
        holdings = _get_holdings()

    total_weight = sum(STOCK_WEIGHTS.values())
    remaining_budget = budget
    allocations = {}

    # Build sortable list: (priority_order, stock_info)
    # Priority 0 = needs funding (sorted by remaining_units asc)
    # Priority 1 = target met or no price
    pending = []
    for ticker in STOCKS:
        weight = STOCK_WEIGHTS.get(ticker, 0)
        target = TARGET_UNITS.get(ticker, 0)
        current = holdings.get(ticker, 0)
        remaining_units = target - current
        price = prices.get(ticker, {}).get("price", 0)
        change_pct = prices.get(ticker, {}).get("change_pct", 0)
        limit_price = _compute_limit_price(price) if price > 0 else 0

        if remaining_units <= 0 or price <= 0:
            # Target met or no price — include with 0 units, no budget needed
            allocations[ticker] = {
                "ticker": ticker,
                "weight": weight,
                "amount_ngn": 0.0,
                "price": price,
                "limit_price": limit_price,
                "units": 0,
                "remaining_units": max(0, remaining_units),
                "change_pct": change_pct,
            }
            if remaining_units <= 0:
                logger.debug("{}: target met ({}/{}) — fully allocated", ticker, current, target)
            continue

        pending.append({
            "ticker": ticker,
            "weight": weight,
            "remaining_units": remaining_units,
            "price": price,
            "change_pct": change_pct,
            "limit_price": limit_price,
        })

    # Sort pending by remaining_units ascending (closest to target = highest priority)
    pending.sort(key=lambda s: s["remaining_units"])

    # Phase 1: Enforce MIN_BUY_COST in priority order
    qualified = []
    for s in pending:
        price = s["price"]
        remaining_units = s["remaining_units"]
        min_units = _min_units_for_cost(price, MIN_BUY_COST)
        cost_for_min = round(min_units * price, 2)

        if remaining_budget < cost_for_min:
            # Can't meet minimum — include with 0 units
            allocations[s["ticker"]] = {
                "ticker": s["ticker"],
                "weight": s["weight"],
                "amount_ngn": 0.0,
                "price": price,
                "limit_price": s["limit_price"],
                "units": 0,
                "remaining_units": remaining_units,
                "change_pct": s["change_pct"],
            }
            logger.debug(
                "{}: can't meet min (need N{:,.2f}, have N{:,.2f}) — skipping",
                s["ticker"], cost_for_min, remaining_budget,
            )
            continue

        # Reserve minimum units
        allocations[s["ticker"]] = {
            "ticker": s["ticker"],
            "weight": s["weight"],
            "amount_ngn": cost_for_min,
            "price": price,
            "limit_price": s["limit_price"],
            "units": min_units,
            "remaining_units": remaining_units - min_units,
            "change_pct": s["change_pct"],
        }
        remaining_budget -= cost_for_min
        qualified.append(s)

    # Phase 2: Distribute remaining budget by weight to qualified stocks
    if qualified and remaining_budget > 0:
        for s in qualified:
            ticker = s["ticker"]
            alloc = allocations[ticker]

            if alloc["remaining_units"] <= 0:
                continue

            weight_share = s["weight"] / total_weight
            extra_budget = round(remaining_budget * weight_share, 2)
            current_cost = alloc["amount_ngn"]
            available = current_cost + extra_budget

            max_additional = alloc["remaining_units"]
            affordable = int(extra_budget // s["price"]) if s["price"] > 0 else 0
            additional = min(max_additional, affordable)

            if additional > 0:
                alloc["units"] += additional
                alloc["amount_ngn"] = round(alloc["units"] * s["price"], 2)
                alloc["remaining_units"] -= additional

    # Log results
    for s in qualified:
        a = allocations[s["ticker"]]
        if a["units"] > 0:
            logger.debug(
                "{}: N{:,.2f} → {} units @ N{:.2f} (limit: N{:.2f})",
                a["ticker"], a["amount_ngn"], a["units"], a["price"], a["limit_price"],
            )

    # Return in original STOCKS order
    return [allocations[t] for t in STOCKS]


def run_dca(dry_run: bool = False) -> dict:
    """Run a DCA round. dry_run=True previews without saving."""
    prices = get_prices()
    if not prices:
        logger.error("No prices available — aborting DCA")
        return {}

    round_date = datetime.now().strftime("%Y-%m-%d")
    allocations = compute_allocations(prices, MONTHLY_BUDGET)
    total = sum(a["amount_ngn"] for a in allocations)

    result = {
        "round_date": round_date,
        "budget": MONTHLY_BUDGET,
        "total_allocated": total,
        "allocations": allocations,
        "dry_run": dry_run,
        "round_id": None,
    }

    if dry_run:
        logger.info("DRY RUN — N{:,.2f} across {} stocks", total, len(allocations))
        return result

    round_id = save_dca_round(round_date, MONTHLY_BUDGET, allocations)
    result["round_id"] = round_id
    logger.info("DCA round {} saved — N{:,.2f} across {} stocks", round_id, total, len(allocations))
    return result


def get_dca_summary() -> str:
    """Return human-readable summary of last DCA round."""
    round_data = get_last_round()
    if not round_data:
        return "No DCA rounds on record."

    lines = [
        f"DCA Round — {round_data['round_date']}",
        f"Budget: N{round_data['total_budget']:,.2f}",
        f"Status: {round_data['status']}",
        "",
        "Allocations:",
    ]
    for a in round_data["allocations"]:
        lines.append(
            f"  {a['ticker']}: N{a['amount_ngn']:,.2f} → {a['units'] or '?'} units @ N{a['price'] or '?'}"
        )

    if round_data.get("stripe_invoice_id"):
        lines.append(f"\nStripe Invoice: {round_data['stripe_invoice_id']}")

    return "\n".join(lines)
