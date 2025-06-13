import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

from .database import (
    init_db,
    add_subscription,
    get_subscription,
    remove_subscription,
    subscription_expired,
    DB_NAME,
)
from .token_manager import generate_token
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # ID del canal a administrar


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Bienvenido. Usa /gen_token <duracion> para obtener un token.")


def gen_token(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        update.message.reply_text("Uso: /gen_token <1d|1w|2w|1m|forever>")
        return
    key = context.args[0]
    token, days = generate_token(key)
    add_subscription(update.effective_user.id, token, days)
    update.message.reply_text(f"Tu token es: {token}. Valido por {days} dias.")


def join(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        update.message.reply_text("Debes proporcionar el token")
        return
    token = context.args[0]
    sub = get_subscription(update.effective_user.id)
    if not sub or sub["token"] != token or subscription_expired(sub):
        update.message.reply_text("Token invalido o expirado")
        return
    context.bot.invite_chat_member(CHANNEL_ID, update.effective_user.id)
    update.message.reply_text("Acceso concedido al canal")


def check_expirations(context: CallbackContext):
    for user_id in context.dispatcher.chat_data.get("subscriptions", {}).keys():
        sub = get_subscription(user_id)
        if sub and subscription_expired(sub):
            logger.info("Expulsando %s por expiracion", user_id)
            context.bot.kick_chat_member(CHANNEL_ID, user_id)
            remove_subscription(user_id)


def stats(update: Update, context: CallbackContext):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM subscriptions")
    count = c.fetchone()[0]
    conn.close()
    update.message.reply_text(f"Usuarios suscritos: {count}")


def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("BOT_TOKEN y CHANNEL_ID deben estar definidos")
    init_db()

    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("gen_token", gen_token))
    dp.add_handler(CommandHandler("join", join))
    dp.add_handler(CommandHandler("stats", stats))

    job_queue = updater.job_queue
    job_queue.run_repeating(check_expirations, interval=3600, first=0)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
