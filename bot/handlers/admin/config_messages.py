import os
from telegram import Update
from telegram.ext import ContextTypes

from ...utils.config import save_config

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update.effective_user.id):
            await update.effective_message.reply_text("⛔ Acceso denegado")
            return
        return await func(update, context)

    return wrapper


@admin_only
async def set_reminder_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("Uso: /set_reminder <mensaje>")
        return
    text = " ".join(context.args)
    save_config("reminder_message", text)
    await update.effective_message.reply_text("Mensaje de recordatorio guardado")


@admin_only
async def set_expiration_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("Uso: /set_expiration <mensaje>")
        return
    text = " ".join(context.args)
    save_config("expiration_message", text)
    await update.effective_message.reply_text("Mensaje de expiración guardado")

