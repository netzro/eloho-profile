from loguru import logger
from eloho.config import STOCKS
from eloho.db import save_prices, get_latest_prices
from eloho.scraper import ngx_scrape_stocks

MAX_FETCH_RETRIES = 2


def fetch_prices() -> list[dict]:
    """Fetch current NGX prices by scraping afx.kwayisi.org."""
    logger.info("Scraping NGX prices for {} stocks", len(STOCKS))

    raw = None
    for attempt in range(MAX_FETCH_RETRIES):
        try:
            raw = ngx_scrape_stocks(STOCKS)
            if raw:
                break
            logger.warning("Empty scrape result (attempt {}/{})", attempt + 1, MAX_FETCH_RETRIES)
        except Exception as e:
            logger.warning("Scrape failed (attempt {}/{}): {}", attempt + 1, MAX_FETCH_RETRIES, e)
            if attempt == MAX_FETCH_RETRIES - 1:
                raise

    if not raw:
        logger.error("All scrape attempts failed")
        return []

    results = []
    for ticker in STOCKS:
        data = raw.get(ticker)
        if not data:
            logger.warning("No data returned for {}", ticker)
            continue
        results.append({
            "ticker": ticker,
            "price": data["price"],
            "change_pct": data.get("change_pct", 0.0),
            "change_abs": data.get("change_abs", 0.0),
            "day_high": data.get("day_high", 0.0),
            "day_low": data.get("day_low", 0.0),
        })
        logger.debug(
            "{}: N{:.2f} ({:+.2f}%)",
            ticker, data["price"], data.get("change_pct", 0.0)
        )

    if results:
        save_prices(results)
        logger.info("Saved prices for {} stocks", len(results))
    return results


def get_prices() -> dict[str, dict]:
    """Get latest prices from DB, fetch fresh if empty."""
    prices = get_latest_prices()
    if not prices:
        logger.info("No cached prices — fetching fresh")
        fetch_prices()
        prices = get_latest_prices()
    return prices


def check_circuit_breakers(prices: list[dict]) -> list[dict]:
    """Flag stocks that hit NGX circuit breaker bands (±10%)."""
    triggered = []
    for p in prices:
        chg = abs(p.get("change_pct", 0))
        if chg >= 9.5:
            triggered.append({
                "ticker": p["ticker"],
                "change_pct": p["change_pct"],
                "direction": "up" if p["change_pct"] > 0 else "down",
            })
            logger.warning(
                "Circuit breaker: {} {:+.2f}%",
                p["ticker"], p["change_pct"]
            )
    return triggered
