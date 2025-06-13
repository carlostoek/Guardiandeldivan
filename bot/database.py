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
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            duration INTEGER,
            used INTEGER DEFAULT 0,
            created_at TEXT
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


def set_setting(key: str, value: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()
    conn.close()


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default


def get_all_subscriptions() -> list[dict]:
    """Return all subscriptions including expired ones."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT user_id, token, start_date, duration, renewals FROM subscriptions"
    )
    rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        result.append(
            {
                "user_id": row[0],
                "token": row[1],
                "start_date": datetime.fromisoformat(row[2]),
                "duration": row[3],
                "renewals": row[4],
            }
        )
    return result


def save_token(token: str, duration: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO tokens (token, duration, used, created_at) VALUES (?, ?, 0, ?)",
        (token, duration, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def use_token(token: str) -> Optional[int]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT duration, used FROM tokens WHERE token=?", (token,))
    row = c.fetchone()
    if not row or row[1]:
        conn.close()
        return None
    duration = row[0]
    c.execute("UPDATE tokens SET used=1 WHERE token=?", (token,))
    conn.commit()
    conn.close()
    return duration

