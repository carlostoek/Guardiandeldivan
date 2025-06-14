import os

from aiogram import Router, types
from aiogram.filters import Command, CommandObject

from ...utils.config import save_config

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


router = Router()


@router.message(Command("set_reminder"))
async def set_reminder_message(message: types.Message, command: CommandObject) -> None:
    """Store custom reminder text."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Acceso denegado")
        return
    if not command.args:
        await message.answer("Uso: /set_reminder <mensaje>")
        return
    save_config("reminder_message", command.args)
    await message.answer("Mensaje de recordatorio guardado")


@router.message(Command("set_expiration"))
async def set_expiration_message(message: types.Message, command: CommandObject) -> None:
    """Store custom expiration text."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Acceso denegado")
        return
    if not command.args:
        await message.answer("Uso: /set_expiration <mensaje>")
        return
    save_config("expiration_message", command.args)
    await message.answer("Mensaje de expiración guardado")

