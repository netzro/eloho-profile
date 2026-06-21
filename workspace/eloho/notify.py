import asyncio
import time
from datetime import datetime
from loguru import logger
from eloho.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_message(text: str, retries: int = 2):
    """Send Telegram message synchronously, with retry on transient failures."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — message not sent")
        logger.info("MSG: {}", text)
        return

    async def _send():
        from telegram import Bot
        from telegram.request import HTTPXRequest

        request = HTTPXRequest(connect_timeout=10, read_timeout=10, pool_timeout=10)
        bot = Bot(token=TELEGRAM_BOT_TOKEN, request=request)
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode="Markdown",
        )

    last_error = None
    for attempt in range(retries + 1):
        try:
            asyncio.run(_send())
            logger.info("Telegram message sent")
            return
        except Exception as e:
            last_error = e
            if attempt < retries:
                wait = 1.5 * (attempt + 1)
                logger.warning("Telegram send failed (attempt {}/{}), retrying in {}s: {}",
                                attempt + 1, retries + 1, wait, e)
                time.sleep(wait)
    logger.error("Telegram send failed after {} attempts: {}", retries + 1, last_error)


def notify_prices(prices: list[dict]):
    """Send price summary notification."""
    lines = ["*Eloho Price Update*", f"_{datetime.now().strftime('%Y-%m-%d %H:%M')} WAT_", ""]
    for p in prices:
        arrow = "🔴" if p.get("change_pct", 0) < 0 else "🟢"
        lines.append(f"{arrow} *{p['ticker']}*: N{p['price']:,.2f} ({p.get('change_pct', 0):+.2f}%)")
    send_message("\n".join(lines))


def notify_circuit_breaker(triggered: list[dict]):
    """Alert when circuit breaker is triggered."""
    for t in triggered:
        direction = "⬆️" if t["direction"] == "up" else "⬇️"
        msg = (
            f"⚠️ *Circuit Breaker Alert*\n"
            f"{direction} *{t['ticker']}* hit {t['change_pct']:+.2f}%\n"
            f"NGX ±10% band triggered"
        )
        send_message(msg)


def notify_dca_complete(round_data: dict, invoice_id: str | None = None):
    """Send DCA round completion summary."""
    budget = round_data.get("budget") or round_data.get("total_budget", 0)
    lines = [
        "✅ *DCA Round Complete*",
        f"Date: {round_data['round_date']}",
        f"Budget: N{budget:,.2f}",
        "",
        "*Allocations:*",
    ]
    for a in round_data["allocations"]:
        lines.append(f"  • *{a['ticker']}*: N{a['amount_ngn']:,.2f} ({a.get('units', '?')} units)")

    if invoice_id:
        lines.append(f"\n📄 Stripe Invoice: `{invoice_id}`")

    send_message("\n".join(lines))


def notify_error(context: str, error: str):
    """Send error alert."""
    msg = f"❌ *Eloho Error*\nContext: {context}\nError: `{error}`"
    send_message(msg)
