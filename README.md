# Eloho — HermesHack 2026 Profile

Autonomous NGX Investment Agent profile for [Hermes Agent](https://hermes-agent.nousresearch.com/) by Nous Research.

## Quick Start

```bash
# Clone this profile
git clone https://github.com/netzro/eloho-profile.git ~/.hermes/profiles/eloho

# Set up Telegram credentials
cp .env.example .env
# Edit .env with your Telegram bot token

# Start Eloho
eloho gateway start

# DM Eloho on Telegram
```

## Agent Capabilities

| Message | Response |
|---|---|
| "Check prices" | Live NGX prices + circuit breaker alerts |
| "Run DCA" | Execute DCA round toward unit targets |
| "Give me a report" | Portfolio with PnL + progress bars |
| "Invoice" | Stripe invoice for last round |
| "Status" | System health check |

## DCA Strategy

- Target-unit tracking (GTCO/ZENITH: 500, OKOMUOIL: 30, MTNN: 50, others: 200)
- Near-target priority
- ₦5,000 minimum per stock
- Weight-based distribution

## Self-Contained

This profile includes the full agent code in `workspace/`:

```
workspace/
├── eloho/          # Core package (cli, dca, prices, scraper, stripe, notify)
├── tests/          # 20 unit tests
├── run.sh          # CLI entry point
└── pyproject.toml  # Python 3.11 project
```

No separate repo needed. Clone → Configure → Run.

## License

MIT — HermesHack 2026
