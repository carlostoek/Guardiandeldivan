from typing import Optional

from database import get_db

__all__ = [
    "get_config",
    "set_config",
]


async def get_config(key: str) -> Optional[str]:
    """Return the configuration value for the given key."""
    db = get_db()
    async with db.execute("SELECT value FROM config WHERE key=?", (key,)) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return str(row["value"])


async def set_config(key: str, value: str) -> None:
    """Set a configuration value."""
    db = get_db()
    await db.execute(
        "INSERT INTO config (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    await db.commit()
