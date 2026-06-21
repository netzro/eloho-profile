import sqlite3
from datetime import datetime
from loguru import logger
from eloho.config import DB_PATH


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            price REAL NOT NULL,
            change_pct REAL,
            fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dca_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_date TEXT NOT NULL,
            total_budget REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            stripe_invoice_id TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dca_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            weight REAL NOT NULL,
            amount_ngn REAL NOT NULL,
            price_at_buy REAL,
            units REAL,
            FOREIGN KEY (round_id) REFERENCES dca_rounds(id)
        );

        CREATE INDEX IF NOT EXISTS idx_prices_ticker ON prices(ticker);
        CREATE INDEX IF NOT EXISTS idx_prices_fetched ON prices(fetched_at);
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized at {}", DB_PATH)


def save_prices(price_data: list[dict]):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    rows = [(d["ticker"], d["price"], d.get("change_pct"), now) for d in price_data]
    cur.executemany(
        "INSERT INTO prices (ticker, price, change_pct, fetched_at) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()


def get_latest_prices() -> dict[str, dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT ticker, price, change_pct, fetched_at
        FROM prices p1
        WHERE fetched_at = (
            SELECT MAX(fetched_at) FROM prices p2 WHERE p2.ticker = p1.ticker
        )
    """)
    rows = cur.fetchall()
    conn.close()
    return {
        row[0]: {"price": row[1], "change_pct": row[2], "fetched_at": row[3]}
        for row in rows
    }


def save_dca_round(round_date: str, budget: float, allocations: list[dict]) -> int:
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO dca_rounds (round_date, total_budget, status, created_at) VALUES (?,?,?,?)",
        (round_date, budget, "pending", now),
    )
    round_id = cur.lastrowid
    rows = [
        (round_id, a["ticker"], a["weight"], a["amount_ngn"], a.get("price"), a.get("units"))
        for a in allocations
    ]
    cur.executemany(
        "INSERT INTO dca_allocations (round_id, ticker, weight, amount_ngn, price_at_buy, units) VALUES (?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return round_id


def update_round_invoice(round_id: int, invoice_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE dca_rounds SET stripe_invoice_id=?, status='invoiced' WHERE id=?",
        (invoice_id, round_id),
    )
    conn.commit()
    conn.close()


def get_last_round() -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.id, r.round_date, r.total_budget, r.status, r.stripe_invoice_id,
               a.ticker, a.weight, a.amount_ngn, a.price_at_buy, a.units
        FROM dca_rounds r
        JOIN dca_allocations a ON a.round_id = r.id
        WHERE r.id = (SELECT MAX(id) FROM dca_rounds)
    """)
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return None
    r = rows[0]
    return {
        "id": r[0],
        "round_date": r[1],
        "total_budget": r[2],
        "status": r[3],
        "stripe_invoice_id": r[4],
        "allocations": [
            {"ticker": row[5], "weight": row[6], "amount_ngn": row[7],
             "price": row[8], "units": row[9]}
            for row in rows
        ],
    }
