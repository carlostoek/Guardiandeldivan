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
    list_active_subscriptions,
    DB_NAME,
)
from .token_manager import generate_token
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # ID del canal a administrar
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_only(func):
    def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            update.message.reply_text("Acceso denegado")
            return
        return func(update, context)

    return wrapper


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Bienvenido. Contacta con un administrador para obtener un token y luego usa /join <token>."
    )


@admin_only
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


@admin_only
def add_sub(update: Update, context: CallbackContext):
    if len(context.args) != 2:
        update.message.reply_text("Uso: /add_sub <user_id> <duracion>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        update.message.reply_text("user_id debe ser numerico")
        return
    key = context.args[1]
    token, days = generate_token(key)
    add_subscription(user_id, token, days)
    update.message.reply_text(f"Suscripcion creada para {user_id}. Token: {token}")


@admin_only
def remove_sub(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        update.message.reply_text("Uso: /remove_sub <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        update.message.reply_text("user_id debe ser numerico")
        return
    remove_subscription(user_id)
    update.message.reply_text("Suscripcion eliminada")


@admin_only
def list_subs(update: Update, context: CallbackContext):
    subs = list_active_subscriptions()
    if not subs:
        update.message.reply_text("No hay suscriptores activos")
        return
    lines = [
        f"{s['user_id']} - {s['start_date'].strftime('%Y-%m-%d')}" for s in subs
    ]
    update.message.reply_text("\n".join(lines))


@admin_only
def admin_help(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Comandos admin:\n"
        "/gen_token <duracion> - Generar token para un usuario\n"
        "/add_sub <user_id> <duracion> - Alta manual\n"
        "/remove_sub <user_id> - Baja manual\n"
        "/list_subs - Listar suscriptores activos"
    )


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
    dp.add_handler(CommandHandler("add_sub", add_sub))
    dp.add_handler(CommandHandler("remove_sub", remove_sub))
    dp.add_handler(CommandHandler("list_subs", list_subs))
    dp.add_handler(CommandHandler("admin", admin_help))

    job_queue = updater.job_queue
    job_queue.run_repeating(check_expirations, interval=3600, first=0)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
