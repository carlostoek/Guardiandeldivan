from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services.config_service import set_pricing
from database import get_db
from bot import messages

router = Router()


async def _ensure_admin(tg_id: int) -> bool:
    db = get_db()
    async with db.execute("SELECT is_admin FROM user WHERE id=?", (tg_id,)) as cur:
        row = await cur.fetchone()
    return bool(row and row["is_admin"] == 1)


@router.message(Command("set_price"))
async def cmd_set_price(message: Message, command: Command.CommandObject) -> None:
    tg_user = message.from_user
    if tg_user is None:
        return
    if not await _ensure_admin(tg_user.id):
        await message.answer(messages.ADMIN_ONLY)
        return
    if not command.args:
        await message.answer("Uso: /set_price <periodo> <cantidad>")
        return
    parts = command.args.split()
    if len(parts) != 2:
        await message.answer("Uso: /set_price <periodo> <cantidad>")
        return
    period = parts[0]
    amount = parts[1]
    await set_pricing(period, amount)
    await message.answer(messages.PRICE_UPDATED.format(period=period, amount=amount))
