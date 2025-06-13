import os
import logging
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

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
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.effective_message.reply_text("Acceso denegado")
            return
        return await func(update, context)

    return wrapper


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Bienvenido. Contacta con un administrador para obtener un token y luego usa /join <token>."
    )


@admin_only
async def gen_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.effective_message.reply_text("Uso: /gen_token <1d|1w|2w|1m|forever>")
        return
    key = context.args[0]
    token, days = generate_token(key)
    add_subscription(update.effective_user.id, token, days)
    await update.effective_message.reply_text(
        f"Tu token es: {token}. Valido por {days} dias."
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.effective_message.reply_text("Debes proporcionar el token")
        return
    token = context.args[0]
    sub = get_subscription(update.effective_user.id)
    if not sub or sub["token"] != token or subscription_expired(sub):
        await update.effective_message.reply_text("Token invalido o expirado")
        return
    invite = await context.bot.create_chat_invite_link(CHANNEL_ID, member_limit=1)
    await update.effective_message.reply_text(
        f"Acceso concedido al canal: {invite.invite_link}"
    )


@admin_only
async def add_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.effective_message.reply_text("Uso: /add_sub <user_id> <duracion>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("user_id debe ser numerico")
        return
    key = context.args[1]
    token, days = generate_token(key)
    add_subscription(user_id, token, days)
    await update.effective_message.reply_text(
        f"Suscripcion creada para {user_id}. Token: {token}"
    )


@admin_only
async def remove_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.effective_message.reply_text("Uso: /remove_sub <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("user_id debe ser numerico")
        return
    remove_subscription(user_id)
    await update.effective_message.reply_text("Suscripcion eliminada")


@admin_only
async def list_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = list_active_subscriptions()
    if not subs:
        await update.effective_message.reply_text("No hay suscriptores activos")
        return
    lines = [
        f"{s['user_id']} - {s['start_date'].strftime('%Y-%m-%d')}" for s in subs
    ]
    await update.effective_message.reply_text("\n".join(lines))


@admin_only
async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Comandos admin:\n"
        "/gen_token <duracion> - Generar token para un usuario\n"
        "/add_sub <user_id> <duracion> - Alta manual\n"
        "/remove_sub <user_id> - Baja manual\n"
        "/list_subs - Listar suscriptores activos"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar los comandos disponibles para cualquier usuario."""
    await update.effective_message.reply_text(
        "Comandos disponibles:\n"
        "/start - Mensaje de bienvenida\n"
        "/join <token> - Unirte al canal con un token valido\n"
        "/stats - Estadisticas basicas\n"
        "/help - Mostrar esta ayuda\n"
        "/menu - Mostrar menu de botones"
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar un menu de botones con los comandos disponibles."""
    keyboard = [
        [InlineKeyboardButton("/help", callback_data="help")],
        [InlineKeyboardButton("/join", callback_data="join")],
        [InlineKeyboardButton("/stats", callback_data="stats")],
    ]
    if is_admin(update.effective_user.id):
        keyboard.extend(
            [
                [InlineKeyboardButton("/gen_token", callback_data="gen_token")],
                [InlineKeyboardButton("/add_sub", callback_data="add_sub")],
                [InlineKeyboardButton("/remove_sub", callback_data="remove_sub")],
                [InlineKeyboardButton("/list_subs", callback_data="list_subs")],
            ]
        )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text("Selecciona una opcion:", reply_markup=reply_markup)


async def menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "help":
        await help_command(update, context)
    elif data == "stats":
        await stats(update, context)
    elif data == "list_subs":
        await list_subs(update, context)
    elif data == "gen_token":
        await query.message.reply_text("Uso: /gen_token <duracion>")
    elif data == "add_sub":
        await query.message.reply_text("Uso: /add_sub <user_id> <duracion>")
    elif data == "remove_sub":
        await query.message.reply_text("Uso: /remove_sub <user_id>")
    elif data == "join":
        await query.message.reply_text("Uso: /join <token>")


async def check_expirations(context: ContextTypes.DEFAULT_TYPE):
    for sub in list_active_subscriptions():
        if subscription_expired(sub):
            user_id = sub["user_id"]
            logger.info("Expulsando %s por expiracion", user_id)
            await context.bot.ban_chat_member(CHANNEL_ID, user_id)
            remove_subscription(user_id)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM subscriptions")
    count = c.fetchone()[0]
    conn.close()
    await update.effective_message.reply_text(f"Usuarios suscritos: {count}")


def main() -> None:
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("BOT_TOKEN y CHANNEL_ID deben estar definidos")

    init_db()

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.job_queue.scheduler.configure(timezone=pytz.utc)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gen_token", gen_token))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("add_sub", add_sub))
    application.add_handler(CommandHandler("remove_sub", remove_sub))
    application.add_handler(CommandHandler("list_subs", list_subs))
    application.add_handler(CommandHandler("admin", admin_help))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(menu_button))

    application.job_queue.run_repeating(check_expirations, interval=3600, first=0)

    application.run_polling()


if __name__ == "__main__":
    main()
