from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import get_db
from services.config_service import set_config

router = Router()


async def _ensure_admin(tg_id: int) -> bool:
    """Return True if the given Telegram ID belongs to an admin user."""
    db = get_db()
    async with db.execute("SELECT is_admin FROM user WHERE id=?", (tg_id,)) as cur:
        row = await cur.fetchone()
    return bool(row and row["is_admin"] == 1)


@router.message(Command("set_reminder"))
async def cmd_set_reminder(message: Message, command: Command.CommandObject) -> None:
    tg_user = message.from_user
    if tg_user is None:
        return
    if not await _ensure_admin(tg_user.id):
        await message.answer("No tienes permiso para usar este comando")
        return

    text = command.args.strip() if command.args else None
    if not text:
        await message.answer("Uso: /set_reminder <texto>")
        return

    await set_config("reminder_msg", text)
    await message.answer("Mensaje de recordatorio actualizado")


@router.message(Command("set_expiration"))
async def cmd_set_expiration(message: Message, command: Command.CommandObject) -> None:
    tg_user = message.from_user
    if tg_user is None:
        return
    if not await _ensure_admin(tg_user.id):
        await message.answer("No tienes permiso para usar este comando")
        return

    text = command.args.strip() if command.args else None
    if not text:
        await message.answer("Uso: /set_expiration <texto>")
        return

    await set_config("expiration_msg", text)
    await message.answer("Mensaje de expiración actualizado")
