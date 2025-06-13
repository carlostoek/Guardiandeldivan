import os
import logging
from datetime import datetime, timedelta
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
    set_setting,
    get_setting,
    get_all_subscriptions,
    DB_NAME,
)
from .token_manager import generate_token, create_token
from .database import use_token
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
    await show_main_menu(
        update,
        context,
        text="Bienvenido. Contacta con un administrador para obtener un token y luego selecciona una opción:",
    )


@admin_only
async def gen_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.effective_message.reply_text("Uso: /gen_token <1d|1w|2w|1m|forever>")
        return
    key = context.args[0]
    token, days = create_token(key)
    await update.effective_message.reply_text(
        f"Tu token es: {token}. Válido por {days} días."
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.effective_message.reply_text("Debes proporcionar el token")
        return
    token = context.args[0]
    duration = use_token(token)
    if not duration:
        await update.effective_message.reply_text("Token invalido o expirado")
        return
    add_subscription(update.effective_user.id, token, duration)
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
async def set_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.effective_message.reply_text("Uso: /set_rate <dias> <monto>")
        return
    try:
        days = int(context.args[0])
        amount = float(context.args[1])
    except ValueError:
        await update.effective_message.reply_text("Valores invalidos")
        return
    set_setting("rate_frequency", str(days))
    set_setting("rate_amount", str(amount))
    await update.effective_message.reply_text(
        f"Tarifa guardada: cada {days} dias por {amount}"
    )


@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("Uso: /broadcast <mensaje>")
        return
    message = " ".join(context.args)
    sent = 0
    for sub in list_active_subscriptions():
        try:
            await context.bot.send_message(sub["user_id"], message)
            sent += 1
        except Exception as exc:
            logger.error("Error enviando a %s: %s", sub["user_id"], exc)
    await update.effective_message.reply_text(f"Mensaje enviado a {sent} usuarios")


@admin_only
async def gen_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.effective_message.reply_text(
            "Uso: /gen_link <user_id> <duracion>"
        )
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("user_id debe ser numerico")
        return
    key = context.args[1]
    token, days = generate_token(key)
    add_subscription(user_id, token, days)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={token}"
    await update.effective_message.reply_text(f"Enlace de acceso: {link}")


@admin_only
async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Comandos admin:\n"
        "/add_sub <user_id> <duracion> - Alta manual\n"
        "/remove_sub <user_id> - Baja manual\n"
        "/list_subs - Listar suscriptores activos\n"
        "/set_rate <dias> <monto> - Configurar tarifa\n"
        "/broadcast <mensaje> - Enviar mensaje a todos\n"
        "/gen_link <user_id> <duracion> - Generar link con token"
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


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = "Selecciona una opcion:"):
    """Mostrar el menu principal adecuando opciones según el rol del usuario."""
    if is_admin(update.effective_user.id):
        keyboard = [
            [InlineKeyboardButton("Configuración", callback_data="configuracion")],
            [InlineKeyboardButton("Administración", callback_data="administracion")],
        ]
    else:
        keyboard = [[InlineKeyboardButton("Solicitar token", callback_data="solicitar_token")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text(text, reply_markup=reply_markup)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar el menu principal."""
    await show_main_menu(update, context)


async def menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "help":
        await help_command(update, context)
    elif data == "stats":
        await stats(update, context)
    elif data == "solicitar_token":
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"El usuario {update.effective_user.id} solicita un token",
                )
            except Exception as exc:
                logger.error("No se pudo notificar a %s: %s", admin_id, exc)
        await query.message.reply_text(
            "Se ha notificado a los administradores, recibirás tu token pronto"
        )
    elif data == "configuracion":
        keyboard = [
            [InlineKeyboardButton("Configurar tarifa", callback_data="set_tarifa")],
            [InlineKeyboardButton("Volver", callback_data="volver")],
        ]
        await query.message.reply_text(
            "Menú de configuración:", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "set_tarifa":
        await query.message.reply_text("Uso: /set_rate <dias> <monto>")
    elif data == "administracion":
        keyboard = [
            [InlineKeyboardButton("Estadísticas", callback_data="admin_stats")],
            [InlineKeyboardButton("Enviar broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("Generar link", callback_data="admin_gen_link")],
            [InlineKeyboardButton("Generar token", callback_data="admin_gen_token")],
            [InlineKeyboardButton("Suscriptores", callback_data="admin_subs")],
            [InlineKeyboardButton("Volver", callback_data="volver")],
        ]
        await query.message.reply_text(
            "Menú de administración:", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "admin_stats":
        await stats(update, context)
    elif data == "admin_broadcast":
        await query.message.reply_text("Uso: /broadcast <mensaje>")
    elif data == "admin_gen_link":
        await query.message.reply_text("Uso: /gen_link <user_id> <duracion>")
    elif data == "admin_gen_token":
        keyboard = [
            [
                InlineKeyboardButton("1 día", callback_data="token_1d"),
                InlineKeyboardButton("1 semana", callback_data="token_1w"),
            ],
            [
                InlineKeyboardButton("2 semanas", callback_data="token_2w"),
                InlineKeyboardButton("1 mes", callback_data="token_1m"),
            ],
            [InlineKeyboardButton("Permanente", callback_data="token_forever")],
            [InlineKeyboardButton("Volver", callback_data="administracion")],
        ]
        await query.message.reply_text(
            "Elige duración para el token:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif data == "admin_subs":
        subs = list_active_subscriptions()
        if not subs:
            await query.message.reply_text("No hay suscriptores activos")
        else:
            keyboard = [
                [
                    InlineKeyboardButton(
                        str(s["user_id"]), callback_data=f"sub_{s['user_id']}"
                    )
                ]
                for s in subs
            ]
            keyboard.append([InlineKeyboardButton("Volver", callback_data="administracion")])
            await query.message.reply_text(
                "Suscriptores:", reply_markup=InlineKeyboardMarkup(keyboard)
            )
    elif data.startswith("sub_"):
        user_id = int(data.split("_")[1])
        sub = get_subscription(user_id)
        if not sub:
            await query.message.reply_text("Suscriptor no encontrado")
        else:
            end_date = sub["start_date"] + timedelta(days=sub["duration"])
            tiempo = datetime.utcnow() - sub["start_date"]
            text = (
                f"ID: {user_id}\n"
                f"Ingreso: {sub['start_date'].strftime('%Y-%m-%d')}\n"
                f"Término: {end_date.strftime('%Y-%m-%d')}\n"
                f"Tiempo en canal: {tiempo.days} días\n"
                f"Renovaciones: {sub['renewals']}"
            )
            keyboard = [
                [InlineKeyboardButton("Expulsar", callback_data=f"expulsar_{user_id}")],
                [InlineKeyboardButton("Volver", callback_data="admin_subs")],
            ]
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("expulsar_"):
        user_id = int(data.split("_")[1])
        await context.bot.ban_chat_member(CHANNEL_ID, user_id)
        remove_subscription(user_id)
        await query.message.reply_text("Usuario expulsado")
    elif data.startswith("token_"):
        key = data.split("_")[1]
        token, days = create_token(key)
        await query.message.reply_text(
            f"Token generado:\n{token}\nVálido por {days} días"
        )
    elif data == "volver":
        await show_main_menu(update, context)
    elif data == "list_subs":
        await list_subs(update, context)
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
    subs = get_all_subscriptions()
    week_ago = datetime.utcnow() - timedelta(days=7)
    total = sum(1 for s in subs if not subscription_expired(s))
    joined_week = sum(1 for s in subs if s["start_date"] >= week_ago)
    left_week = sum(
        1
        for s in subs
        if (s["start_date"] + timedelta(days=s["duration"])) >= week_ago
        and subscription_expired(s)
    )
    reactions = 0  # TODO: obtener reacciones del canal
    text = (
        f"📊 <b>Estadísticas</b>\n"
        f"👥 Suscriptores activos: <b>{total}</b>\n"
        f"✅ Entraron esta semana: <b>{joined_week}</b>\n"
        f"❌ Salieron esta semana: <b>{left_week}</b>\n"
        f"👍 Reacciones totales: <b>{reactions}</b>"
    )
    await update.effective_message.reply_html(text)


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
    application.add_handler(CommandHandler("set_rate", set_rate))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("gen_link", gen_link))
    application.add_handler(CommandHandler("admin", admin_help))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(menu_button))

    application.job_queue.run_repeating(check_expirations, interval=3600, first=0)

    application.run_polling()


if __name__ == "__main__":
    main()
