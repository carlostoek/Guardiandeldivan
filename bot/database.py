import sqlite3
from datetime import datetime, timedelta
from typing import Optional

DB_NAME = "subscriptions.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            token TEXT UNIQUE,
            start_date TEXT,
            duration INTEGER,
            renewals INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


def add_subscription(user_id: int, token: str, duration: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    start_date = datetime.utcnow().isoformat()
    c.execute(
        "INSERT OR REPLACE INTO subscriptions (user_id, token, start_date, duration, renewals) VALUES (?, ?, ?, ?, COALESCE((SELECT renewals FROM subscriptions WHERE user_id=?),0))",
        (user_id, token, start_date, duration, user_id),
    )
    conn.commit()
    conn.close()


def get_subscription(user_id: int) -> Optional[dict]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT user_id, token, start_date, duration, renewals FROM subscriptions WHERE user_id=?",
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "token": row[1],
            "start_date": datetime.fromisoformat(row[2]),
            "duration": row[3],
            "renewals": row[4],
        }
    return None


def remove_subscription(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def subscription_expired(sub: dict) -> bool:
    if not sub:
        return True
    end_date = sub["start_date"] + timedelta(days=sub["duration"])
    return datetime.utcnow() > end_date


def list_active_subscriptions() -> list[dict]:
    """Return a list of active subscriptions with parsed dates."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT user_id, token, start_date, duration, renewals FROM subscriptions"
    )
    rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        sub = {
            "user_id": row[0],
            "token": row[1],
            "start_date": datetime.fromisoformat(row[2]),
            "duration": row[3],
            "renewals": row[4],
        }
        if not subscription_expired(sub):
            result.append(sub)
    return result

