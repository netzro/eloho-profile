# Eloho — Autonomous NGX Investment Agent

> **HermesHack 2026 Submission** — Built on [Hermes Agent](https://hermes-agent.nousresearch.com/) by Nous Research, with Stripe financial rails.

Eloho is an autonomous dollar-cost averaging (DCA) agent that operates on the Nigerian Stock Exchange (NGX). It tracks unit targets, enforces minimum buy thresholds, detects circuit breakers, generates Stripe invoices, and reports progress — all via **Telegram DM**. No CLI needed. Just text Eloho.

---

## 🎯 Why Eloho

70% of Nigerian retail investors lose money by not investing consistently. Eloho solves this by:

- **Autonomous DCA** — buys toward predefined unit targets every round
- **Market-aware** — detects NGX circuit breakers (±10%) and halts trading
- **Target-unit tracking** — prioritizes stocks closest to their target
- **Stripe-ready** — generates invoices the moment rails are available
- **Observable** — cumulative PnL, progress bars, live price alerts

---

## 🚀 How It Works

Eloho runs as a **Hermes Agent** with profile `eloho`. You interact entirely via **Telegram DM**:

**User → Eloho (via Telegram):**
```
"Check prices"
```

**Eloho responds live:**
```
NGX Prices (21:25):

  GTCO         ₦115.55  ▼ 9.97% ⚠️
  ZENITHBANK   ₦110.00  ▼ 4.76%
  OKOMUOIL     ₦1,418.00  0.00%
  TRANSCORP    ₦44.00  0.00%
  MTNN         ₦800.00  0.00%
  ACCESSCORP   ₦22.80  ▼ 0.87%
  FIDSON       ₦101.20  0.00%

⚠️ Circuit breaker: GTCO -9.97%
Telegram alert sent ✅
```

```
"Run DCA"
```

```
DCA Round — 2026-06-21
Budget: ₦40,000.00
Allocated: ₦38,827.40

  GTCO         ₦6,009  → 69 units @ ₦115.55
  ZENITHBANK   ₦6,050  → 72 units @ ₦110.00
  OKOMUOIL     ₦5,672  → 4 units  @ ₦1,418.00
  TRANSCORP    ₦5,016  → 108 units @ ₦44.00
  MTNN         ₦5,600  → 7 units  @ ₦800.00
  ACCESSCORP   ₦5,016  → 220 units @ ₦22.80  ✅ TARGET MET
  FIDSON       ₦5,465  → 54 units @ ₦101.20

DCA round saved ✅
Invoice: in_a0da5ac844e34f4b
```

```
"Give me a report"
```

```
╔══════════════════════════════════════════════════╗
║     ELOHO — Autonomous NGX Investment Agent      ║
╚══════════════════════════════════════════════════╝

Report: 2026-06-21 23:02 WAT

── Portfolio ──────────────────────────────────────
  GTCO           121/500 units  ₦14,009 → ₦13,982  (24.2%)  PnL: -₦27
  ZENITHBANK     127/500 units  ₦14,050 → ₦13,970  (25.4%)  PnL: -₦80
  OKOMUOIL         8/30 units   ₦11,672 → ₦11,344  (26.7%)  PnL: -₦328
  TRANSCORP      204/200 units  ₦9,016 → ₦8,976   (102%)   ✅
  MTNN            14/50 units   ₦11,600 → ₦11,200  (28.0%)  PnL: -₦400
  ACCESSCORP     395/200 units  ₦9,016 → ₦9,006   (198%)   ✅
  FIDSON          93/200 units   ₦9,465 → ₦9,412   (46.5%)  PnL: -₦53

  TOTAL                        ₦78,827 → ₦77,889
  Portfolio PnL: -₦938

── Autonomy Features ──────────────────────────────
  ✅ Automated DCA with target-unit tracking
  ✅ Stripe invoice generation (mock/live)
  ✅ Circuit breaker detection & Telegram alerts
  ✅ Near-target priority allocation
  ✅ Cumulative PnL tracking
  ✅ Fully autonomous via Telegram DM
```

---

## 📱 Telegram UX

Eloho is controlled entirely through **natural language via Telegram**:

| User says | Eloho does |
|---|---|
| "Check prices" | Scrapes live NGX prices, shows change %, alerts on circuit breakers |
| "Run DCA" | Executes DCA round, shows allocation, saves to DB, generates invoice |
| "Give me a report" | Full portfolio report with PnL, progress bars, cumulative tracking |
| "Status" | System health: API status, last DCA round, database state |
| "Invoice" | Creates Stripe invoice for last round, sends URL via Telegram |

---

## 🏗️ Architecture

```
eloho/
├── cli.py          # Optional CLI (fallback)
├── dca.py          # Core allocation engine: target-unit DCA + priority + min-₦5k
├── config.py       # All config hardcoded (secrets only in .env)
├── db.py           # SQLite with WAL mode + foreign keys
├── prices.py       # NGX price scraper with retry logic
├── scraper.py      # afx.kwayisi.org scraper
├── stripe_rails.py # Stripe integration with automatic mock fallback
├── stripe_mock.py  # Mock Stripe for offline/demo
├── notify.py       # Telegram notifications
├── eloho.py        # Portfolio summary with PnL, state export
└── log.py          # Structured logging to log.md
```

**Runtime:**
```
~/.hermes/profiles/eloho/    # Hermes Agent profile (connected platforms, state)
Telegram DM → Hermes Agent (eloho) → Eloho scrapes prices → computes DCA → executes round → generates invoice → sends alert
```

---

## 💡 DCA Strategy

1. **Target-unit tracking** — Each stock has a unit target (GTCO/ZENITH: 500, OKOMUOIL: 30, MTNN: 50, TRANSCORP/ACCESSCORP/FIDSON: 200)
2. **Near-target priority** — Stocks closest to target get funded first
3. **₦5,000 minimum** — No micro-transactions
4. **Whole units only** — `floor()`, no fractions
5. **Weight-based distribution** — Budget split proportional to targets
6. **Circuit breaker guard** — Halts on ±10% NGX band

---

## ⚙️ Configuration

All DCA config in `eloho/config.py`. Secrets in `.env`:

```env
NGXPULSE_API_KEY=your_key       # Optional — mock mode if unset
STRIPE_CUSTOMER_ID=cus_xxx        # Optional
TELEGRAM_BOT_TOKEN=***            # Required for Telegram
TELEGRAM_CHAT_ID=xxx              # Required for Telegram
MONTHLY_BUDGET=40000              # NGN per DCA round
```

Hermes profile:
```yaml
# ~/.hermes/profiles/eloho/config.yaml
# Connected platforms: telegram
```

---

## 🧪 Testing

```bash
cd /data/data/com.termux/files/home/projects/eloho-agent
uv run python -m pytest tests/ -v
```

20 unit tests covering allocation logic, edge cases, and weight derivation.

---

## 🎬 Demo Video Script (1-3 min)

**Record your Telegram screen sharing with Eloho:**

1. **(0:00-0:10)** Hook: "Nigerian investors lose money by not investing. Meet Eloho — my autonomous agent."
2. **(0:10-0:30)** Send "Check prices" via Telegram → Eloho responds with live prices + circuit breaker alert
3. **(0:30-1:00)** Send "Run DCA" → Eloho computes allocation, saves round, generates Stripe invoice
4. **(0:00-1:30)** Send "Give me a report" → Show cumulative PnL, progress bars
5. **(1:30-2:00)** Close: "Fully autonomous. Stripe-ready. Runs on Hermes Agent by Nous Research."

---

## 🏆 Hackathon Highlights

- **Fully autonomous via Telegram** — no CLI, just text
- **Market-aware** — real NGX circuit breaker detection (GTCO -9.97% on submission day)
- **Stripe-ready** — mock now, live the moment API key is set
- **Forward-compatible** — architected for global rails
- **Real data** — live prices from afx.kwayisi.org
- **Observable** — cumulative PnL, progress tracking
- **Battle-tested** — 2 rounds executed, 7 stocks tracked, ₦78K+ deployed

---

## 📊 Live Portfolio

| Stock | Target | Holdings | Spent | Value | PnL | Progress |
|---|---|---|---|---|---|---|
| GTCO | 500 | 121 | ₦14,009 | ₦13,982 | -₦27 | 24.2% |
| ZENITHBANK | 500 | 127 | ₦14,050 | ₦13,970 | -₦80 | 25.4% |
| OKOMUOIL | 30 | 8 | ₦11,672 | ₦11,344 | -₦328 | 26.7% |
| TRANSCORP | 200 | 204 | ₦9,016 | ₦8,976 | -₦40 | ✅ 102% |
| MTNN | 50 | 14 | ₦11,600 | ₦11,200 | -₦400 | 28.0% |
| ACCESSCORP | 200 | 395 | ₦9,016 | ₦9,006 | -₦10 | ✅ 198% |
| FIDSON | 200 | 93 | ₦9,465 | ₦9,412 | -₦53 | 46.5% |

---

## 📄 License

MIT — HermesHack 2026 Submission
