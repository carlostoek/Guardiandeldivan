from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import get_db
from services.subscription_service import add_subscription
from services.token_service import generate_token, validate_token, mark_token_as_used

router = Router()


@router.message(Command("gen_token"))
async def cmd_gen_token(message: Message, command: Command.CommandObject) -> None:
    db = get_db()
    tg_user = message.from_user
    if tg_user is None:
        return

    # Check admin status
    async with db.execute("SELECT is_admin FROM user WHERE id=?", (tg_user.id,)) as cur:
        row = await cur.fetchone()
    if not (row and row["is_admin"] == 1):
        await message.answer("No tienes permiso para usar este comando")
        return

    try:
        days = int(command.args.strip()) if command.args else 0
    except ValueError:
        days = 0
    if days <= 0:
        await message.answer("Uso: /gen_token &lt;días&gt;")
        return

    token = await generate_token(days)
    await message.answer(f"Token generado: <code>{token}</code>")


@router.message(Command("join"))
async def cmd_join(message: Message, command: Command.CommandObject) -> None:
    db = get_db()
    tg_user = message.from_user
    if tg_user is None:
        return

    await db.execute(
        "INSERT OR IGNORE INTO user (id, username, full_name) VALUES (?, ?, ?)",
        (tg_user.id, tg_user.username or "", tg_user.full_name or ""),
    )
    await db.commit()

    token = command.args.strip() if command.args else None
    if not token:
        await message.answer("Uso: /join &lt;token&gt;")
        return

    duration = await validate_token(token)
    if duration is None:
        await message.answer("Token inválido")
        return

    await mark_token_as_used(token)
    await add_subscription(tg_user.id, duration)
    await message.answer(f"Suscripción activada por {duration} días")
