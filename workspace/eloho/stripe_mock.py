"""
stripe_mock.py — Mock Stripe for demo/development.
Mimics real Stripe responses without any API calls.
Swap stripe_rails.py import to this for offline demo.
"""
import uuid
from datetime import datetime
from loguru import logger
from eloho.config import LOG_PATH

NGN_TO_USD_RATE = 1600


def _fake_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def create_dca_invoice(round_data: dict) -> str:
    """Mock Stripe invoice creation."""
    invoice_id = _fake_id("in")
    total_usd = round_data["total_budget"] / NGN_TO_USD_RATE

    logger.info("MOCK Stripe invoice created: {}", invoice_id)
    logger.info("Total: N{:,.2f} (~${:.2f})", round_data["total_budget"], total_usd)

    lines = [
        f"\n## Stripe Invoice (MOCK) — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Invoice ID: {invoice_id}",
        f"Round: {round_data['round_date']}",
        f"Total NGN: N{round_data['total_budget']:,.2f}",
        f"Total USD: ~${total_usd:.2f}",
        "",
        "Line Items:",
    ]
    for a in round_data.get("allocations", []):
        usd = a["amount_ngn"] / NGN_TO_USD_RATE
        lines.append(
            f"  {a['ticker']}: N{a['amount_ngn']:,.2f} (~${usd:.2f}) "
            f"— {a.get('units', '?')} units @ N{a.get('price', '?')}"
        )

    with open(LOG_PATH, "a") as f:
        f.write("\n".join(lines) + "\n")

    return invoice_id


def create_invoice_for_last_round() -> str | None:
    from eloho.db import get_last_round, update_round_invoice
    round_data = get_last_round()
    if not round_data:
        logger.error("No DCA round found")
        return None
    if round_data.get("stripe_invoice_id"):
        logger.info("Already invoiced: {}", round_data["stripe_invoice_id"])
        return round_data["stripe_invoice_id"]
    invoice_id = create_dca_invoice(round_data)
    if invoice_id and round_data.get("id"):
        update_round_invoice(round_data["id"], invoice_id)
    return invoice_id


def get_invoice_url(invoice_id: str) -> str:
    """Return a fake hosted invoice URL for demo."""
    return f"https://invoice.stripe.com/i/mock/{invoice_id}"
