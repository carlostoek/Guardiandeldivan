from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import get_db
from services.subscription_service import add_subscription, remove_subscription

router = Router()


async def _ensure_admin(tg_id: int) -> bool:
    """Return True if the given Telegram ID belongs to an admin user."""
    db = get_db()
    async with db.execute("SELECT is_admin FROM user WHERE id=?", (tg_id,)) as cur:
        row = await cur.fetchone()
    return bool(row and row["is_admin"] == 1)


@router.message(Command("add_sub"))
async def cmd_add_sub(message: Message, command: Command.CommandObject) -> None:
    db = get_db()
    tg_user = message.from_user
    if tg_user is None:
        return
    if not await _ensure_admin(tg_user.id):
        await message.answer("No tienes permiso para usar este comando")
        return

    if not command.args:
        await message.answer("Uso: /add_sub &lt;@user&gt; &lt;d\u00edas&gt;")
        return

    parts = command.args.split()
    if len(parts) != 2:
        await message.answer("Uso: /add_sub &lt;@user&gt; &lt;d\u00edas&gt;")
        return

    username = parts[0].lstrip("@").strip()
    try:
        days = int(parts[1])
    except ValueError:
        await message.answer("Uso: /add_sub &lt;@user&gt; &lt;d\u00das&gt;")
        return

    async with db.execute("SELECT id FROM user WHERE username=?", (username,)) as cur:
        row = await cur.fetchone()
    if not row:
        await message.answer("Usuario no encontrado")
        return

    await add_subscription(int(row["id"]), days)
    await message.answer(f"Suscripci\u00f3n a\u00f1adida por {days} d\u00edas para @{username}")


@router.message(Command("remove_sub"))
async def cmd_remove_sub(message: Message, command: Command.CommandObject) -> None:
    db = get_db()
    tg_user = message.from_user
    if tg_user is None:
        return
    if not await _ensure_admin(tg_user.id):
        await message.answer("No tienes permiso para usar este comando")
        return

    if not command.args:
        await message.answer("Uso: /remove_sub &lt;@user&gt;")
        return

    username = command.args.strip().lstrip("@").strip()
    async with db.execute("SELECT id FROM user WHERE username=?", (username,)) as cur:
        row = await cur.fetchone()
    if not row:
        await message.answer("Usuario no encontrado")
        return

    await remove_subscription(int(row["id"]))
    await message.answer(f"Suscripci\u00f3n eliminada para @{username}")
