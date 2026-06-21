"""
stripe_rails.py — Stripe integration with automatic mock fallback.
If STRIPE_API_KEY is not set or invalid, falls back to stripe_mock.py.
"""
from loguru import logger
from eloho.config import STRIPE_API_KEY

NGN_TO_USD_RATE = 1600


def _is_valid_key(key: str) -> bool:
    """Check if the Stripe key looks like a real key, not a placeholder."""
    if not key:
        return False
    if "***" in key or "xxx" in key or "your" in key.lower() or "placeholder" in key.lower():
        return False
    if not (key.startswith("sk_test_") or key.startswith("sk_live_")):
        return False
    return len(key) > 20


def _get_stripe_module():
    """Lazily import and return the stripe module, or None if unavailable."""
    if not _is_valid_key(STRIPE_API_KEY):
        return None
    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_API_KEY
        return _stripe
    except ImportError:
        return None


def _use_mock() -> bool:
    """Check if we should use mock mode."""
    if not _is_valid_key(STRIPE_API_KEY):
        logger.info("Stripe: mock mode (no valid API key)")
        return True
    if _get_stripe_module() is None:
        logger.info("Stripe: mock mode (stripe package not installed)")
        return True
    logger.info("Stripe: live mode (test key detected)")
    return False


def ngn_to_usd_cents(ngn_amount: float) -> int:
    usd = ngn_amount / NGN_TO_USD_RATE
    return max(1, int(usd * 100))


def create_dca_invoice(round_data: dict) -> str | None:
    use_mock = _use_mock()
    if use_mock:
        from eloho.stripe_mock import create_dca_invoice as mock_invoice
        return mock_invoice(round_data)

    stripe = _get_stripe_module()
    from eloho.config import STRIPE_CUSTOMER_ID
    if not STRIPE_CUSTOMER_ID:
        logger.warning("STRIPE_CUSTOMER_ID not set")
        return None

    try:
        invoice = stripe.Invoice.create(
            customer=STRIPE_CUSTOMER_ID,
            description=f"NGX DCA Round — {round_data['round_date']}",
            metadata={
                "round_id": str(round_data.get("id", "")),
                "round_date": round_data["round_date"],
                "total_ngn": str(round_data["total_budget"]),
                "agent": "eloho",
            },
            currency="usd",
            auto_advance=False,
        )
        for a in round_data["allocations"]:
            stripe.InvoiceItem.create(
                customer=STRIPE_CUSTOMER_ID,
                invoice=invoice.id,
                amount=ngn_to_usd_cents(a["amount_ngn"]),
                currency="usd",
                description=(
                    f"{a['ticker']}: N{a['amount_ngn']:,.2f} "
                    f"({a.get('units','?')} units @ N{a.get('price','?')})"
                ),
            )
        invoice = stripe.Invoice.finalize_invoice(invoice.id)
        logger.info("Stripe invoice: {}", invoice.id)
        return invoice.id
    except Exception as e:
        logger.error("Stripe error: {}", e)
        return None


def create_invoice_for_last_round() -> str | None:
    if _use_mock():
        from eloho.stripe_mock import create_invoice_for_last_round as mock_fn
        return mock_fn()

    from eloho.db import get_last_round, update_round_invoice
    round_data = get_last_round()
    if not round_data:
        logger.error("No DCA round found")
        return None
    if round_data.get("stripe_invoice_id"):
        return round_data["stripe_invoice_id"]
    invoice_id = create_dca_invoice(round_data)
    if invoice_id and round_data.get("id"):
        update_round_invoice(round_data["id"], invoice_id)
    return invoice_id


def get_invoice_url(invoice_id: str) -> str | None:
    if _use_mock():
        from eloho.stripe_mock import get_invoice_url as mock_url
        return mock_url(invoice_id)
    stripe = _get_stripe_module()
    try:
        invoice = stripe.Invoice.retrieve(invoice_id)
        return invoice.get("hosted_invoice_url")
    except Exception as e:
        logger.error("Stripe retrieve error: {}", e)
        return None
