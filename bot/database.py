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
            renewals INTEGER DEFAULT 0,
            reminder_sent INTEGER DEFAULT 0
        )
        """
    )
    try:
        c.execute("ALTER TABLE subscriptions ADD COLUMN reminder_sent INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            join_date TEXT,
            expiration_date TEXT,
            reminded INTEGER DEFAULT 0,
            expired_notified INTEGER DEFAULT 0
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
        "INSERT OR REPLACE INTO subscriptions (user_id, token, start_date, duration, renewals, reminder_sent) VALUES (?, ?, ?, ?, COALESCE((SELECT renewals FROM subscriptions WHERE user_id=?),0), 0)",
        (user_id, token, start_date, duration, user_id),
    )
    conn.commit()
    conn.close()


def get_subscription(user_id: int) -> Optional[dict]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT user_id, token, start_date, duration, renewals, reminder_sent FROM subscriptions WHERE user_id=?",
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
            "reminder_sent": row[5],
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
        "SELECT user_id, token, start_date, duration, renewals, reminder_sent FROM subscriptions"
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
            "reminder_sent": row[5],
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
        "SELECT user_id, token, start_date, duration, renewals, reminder_sent FROM subscriptions"
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
                "reminder_sent": row[5],
            }
        )
    return result


def mark_reminder_sent(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "UPDATE subscriptions SET reminder_sent=1 WHERE user_id=?",
        (user_id,),
    )
    conn.commit()
    conn.close()


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


def list_tokens(
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> list[dict]:
    """Return tokens with optional filtering by user and date range."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    query = (
        "SELECT t.token, t.duration, t.used, t.created_at, s.user_id "
        "FROM tokens t LEFT JOIN subscriptions s ON t.token = s.token"
    )
    conditions = []
    params = []
    if start_date:
        conditions.append("t.created_at >= ?")
        params.append(start_date.isoformat())
    if end_date:
        conditions.append("t.created_at <= ?")
        params.append(end_date.isoformat())
    if user_id is not None:
        conditions.append("s.user_id = ?")
        params.append(user_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY t.created_at DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        result.append(
            {
                "token": row[0],
                "duration": row[1],
                "used": bool(row[2]),
                "created_at": datetime.fromisoformat(row[3]),
                "user_id": row[4],
            }
        )
    return result


# ---- New subscription helpers ----

def add_user_subscription(user_id: int, username: str, full_name: str, expiration_date: datetime):
    """Register or update a user subscription."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    join_date = datetime.utcnow().isoformat()
    c.execute(
        """
        INSERT OR REPLACE INTO user_subscriptions
            (user_id, username, full_name, join_date, expiration_date, reminded, expired_notified)
        VALUES (?, ?, ?, ?, ?, COALESCE((SELECT reminded FROM user_subscriptions WHERE user_id=?),0),
                COALESCE((SELECT expired_notified FROM user_subscriptions WHERE user_id=?),0))
        """,
        (user_id, username, full_name, join_date, expiration_date.isoformat(), user_id, user_id),
    )
    conn.commit()
    conn.close()


def get_all_user_subscriptions() -> list[dict]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT user_id, username, full_name, join_date, expiration_date, reminded, expired_notified FROM user_subscriptions"
    )
    rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        result.append(
            {
                "user_id": row[0],
                "username": row[1],
                "full_name": row[2],
                "join_date": datetime.fromisoformat(row[3]),
                "expiration_date": datetime.fromisoformat(row[4]),
                "reminded": row[5],
                "expired_notified": row[6],
            }
        )
    return result


def get_user_subscription(user_id: int) -> Optional[dict]:
    """Retrieve a user subscription if it exists."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT user_id, username, full_name, join_date, expiration_date, reminded, expired_notified FROM user_subscriptions WHERE user_id=?",
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "username": row[1],
            "full_name": row[2],
            "join_date": datetime.fromisoformat(row[3]),
            "expiration_date": datetime.fromisoformat(row[4]),
            "reminded": row[5],
            "expired_notified": row[6],
        }
    return None


def mark_user_reminded(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "UPDATE user_subscriptions SET reminded=1 WHERE user_id=?",
        (user_id,),
    )
    conn.commit()
    conn.close()


def mark_user_expired_notified(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "UPDATE user_subscriptions SET expired_notified=1 WHERE user_id=?",
        (user_id,),
    )
    conn.commit()
    conn.close()
