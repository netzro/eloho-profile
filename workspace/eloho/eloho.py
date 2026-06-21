"""
eloho.py — Autonomous NGX Investment Agent
Hackathon-ready with Stripe spend, auto-provisioning, and full autonomy.
"""
import json
from datetime import datetime
from pathlib import Path
from eloho.config import LOG_PATH, TARGET_UNITS, STOCKS, MONTHLY_BUDGET
from eloho.db import get_conn, get_last_round
from eloho.prices import get_prices
from eloho.dca import compute_allocations


def _get_cumulative_holdings() -> dict[str, dict]:
    """Get total units, spend, and avg cost per ticker across all rounds."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.ticker,
               SUM(a.units) as total_units,
               SUM(a.amount_ngn) as total_spent,
               AVG(a.price_at_buy) as avg_price,
               COUNT(DISTINCT a.round_id) as rounds
        FROM dca_allocations a
        JOIN dca_rounds r ON r.id = a.round_id
        GROUP BY a.ticker
    """)
    result = {}
    for row in cur.fetchall():
        result[row[0]] = {
            "total_units": int(row[1] or 0),
            "total_spent": round(row[2] or 0, 2),
            "avg_price": round(row[3] or 0, 2),
            "rounds": row[4],
        }
    conn.close()
    return result


def generate_portfolio_summary() -> str:
    """Generate a comprehensive portfolio summary for hackathon demo."""
    prices = get_prices()
    holdings = _get_cumulative_holdings()
    last_round = get_last_round()

    lines = [
        "╔══════════════════════════════════════════════╗",
        "║     ELOHO — Autonomous NGX Investment Agent  ║",
        "╚══════════════════════════════════════════════╝",
        "",
        f"Report: {datetime.now().strftime('%Y-%m-%d %H:%M WAT')}",
        f"Budget/round: N{MONTHLY_BUDGET:,.2f}",
        "",
        "── Portfolio ──────────────────────────────────",
    ]

    total_value = 0.0
    total_spent = 0.0

    for ticker in STOCKS:
        h = holdings.get(ticker, {"total_units": 0, "total_spent": 0, "avg_price": 0, "rounds": 0})
        price_data = prices.get(ticker, {})
        price = price_data.get("price", 0)
        units = h["total_units"]
        spent = h["total_spent"]
        value = round(units * price, 2)
        total_value += value
        total_spent += spent
        target = TARGET_UNITS.get(ticker, 0)
        pct = (units / target * 100) if target > 0 else 0
        avg = h["avg_price"]
        pnl = round(value - spent, 2)
        pnl_pct = ((price - avg) / avg * 100) if avg > 0 else 0

        lines.append(f"  {ticker:12} {units:>5}/{target} units  N{spent:>10,.2f} → N{value:>10,.2f}  ({pct:>5.1f}%)  PnL: {pnl:>+,.2f} ({pnl_pct:+.1f}%)")

    lines.append("")
    lines.append(f"  {'TOTAL':12} {'':>5}         N{total_spent:>10,.2f} → N{total_value:>10,.2f}")
    lines.append(f"  Portfolio PnL: N{total_value - total_spent:>+,.2f}")
    lines.append("")

    if last_round:
        lines.append("── Last DCA Round ─────────────────────────────")
        lines.append(f"  Date: {last_round['round_date']}")
        lines.append(f"  Status: {last_round['status']}")
        if last_round.get("stripe_invoice_id"):
            lines.append(f"  Invoice: {last_round['stripe_invoice_id']}")
        lines.append("")

    lines.append("── Autonomy Features ──────────────────────────")
    lines.append("  ✅ Automated DCA with target-unit tracking")
    lines.append("  ✅ Stripe invoice generation (mock/live)")
    lines.append("  ✅ Circuit breaker detection & alerts")
    lines.append("  ✅ Near-target priority allocation")
    lines.append("  ✅ Cumulative PnL tracking")
    lines.append("  ✅ Telegram notifications")
    lines.append("  ✅ JSON API output for integration")

    return "\n".join(lines)


def generate_stripe_proposal() -> dict:
    """Generate a Stripe-ready invoice proposal for the next DCA round."""
    prices = get_prices()
    holdings = _get_cumulative_holdings()
    allocations = compute_allocations(prices, MONTHLY_BUDGET, holdings=holdings)

    line_items = []
    total = 0.0
    for a in allocations:
        if a["units"] > 0:
            line_items.append({
                "ticker": a["ticker"],
                "units": a["units"],
                "unit_price_ngn": a["price"],
                "total_ngn": a["amount_ngn"],
            })
            total += a["amount_ngn"]

    return {
        "type": "dca_round",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_ngn": round(total, 2),
        "total_usd": round(total / 1600, 2),
        "line_items": line_items,
        "metadata": {
            "agent": "eloho",
            "strategy": "target-unit-dca",
            "stocks": len([a for a in allocations if a["units"] > 0]),
        },
    }


def export_state() -> dict:
    """Export full agent state for backup/inspection."""
    prices = get_prices()
    holdings = _get_cumulative_holdings()
    last_round = get_last_round()

    return {
        "exported_at": datetime.now().isoformat(),
        "config": {
            "monthly_budget": MONTHLY_BUDGET,
            "target_units": TARGET_UNITS,
            "stocks": STOCKS,
        },
        "prices": prices,
        "holdings": holdings,
        "last_round": last_round,
    }
