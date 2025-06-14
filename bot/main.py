import os
import logging
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from .messages import MESSAGES as MSG
from .handlers.user.start import start
from .handlers.admin.config_messages import (
    set_reminder_message,
    set_expiration_message,
)
from .services.subscription_monitor import setup_subscription_monitor

from .database import (
    init_db,
    add_subscription,
    get_subscription,
    remove_subscription,
    subscription_expired,
    list_active_subscriptions,
    list_tokens,
    set_setting,
    get_setting,
    get_all_subscriptions,
)
from .token_manager import generate_token, create_token
from .database import use_token
from .utils.config import init_config

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
            await update.effective_message.reply_text(MSG["access_denied"])
            return
        return await func(update, context)

    return wrapper




@admin_only
async def gen_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.effective_message.reply_text(MSG["gen_token_usage"])
        return
    key = context.args[0]
    token, days = create_token(key)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={token}"
    await update.effective_message.reply_text(
        MSG["gen_token_result"].format(link=link, days=days)
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.effective_message.reply_text(MSG["join_token_missing"])
        return
    token = context.args[0]
    duration = use_token(token)
    if not duration:
        await update.effective_message.reply_text(MSG["join_token_invalid"])
        return
    add_subscription(update.effective_user.id, token, duration)
    invite = await context.bot.create_chat_invite_link(CHANNEL_ID, member_limit=1)
    await update.effective_message.reply_text(
        MSG["join_success"].format(link=invite.invite_link)
    )


@admin_only
async def add_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.effective_message.reply_text(MSG["add_sub_usage"])
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text(MSG["add_sub_user_id_numeric"])
        return
    key = context.args[1]
    token, days = generate_token(key)
    add_subscription(user_id, token, days)
    await update.effective_message.reply_text(
        MSG["add_sub_success"].format(user_id=user_id, token=token)
    )


@admin_only
async def remove_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.effective_message.reply_text(MSG["remove_sub_usage"])
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text(MSG["remove_sub_user_id_numeric"])
        return
    remove_subscription(user_id)
    await update.effective_message.reply_text(MSG["remove_sub_success"])


@admin_only
async def list_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = list_active_subscriptions()
    if not subs:
        await update.effective_message.reply_text(MSG["list_subs_none"])
        return
    lines = [
        f"{s['user_id']} - {s['start_date'].strftime('%Y-%m-%d')}" for s in subs
    ]
    await update.effective_message.reply_text("\n".join(lines))


@admin_only
async def list_tokens_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar tokens generados con filtros opcionales."""
    user_id = None
    start_date = None
    end_date = None
    for arg in context.args:
        if arg.isdigit():
            user_id = int(arg)
        else:
            try:
                dt = datetime.fromisoformat(arg)
            except ValueError:
                await update.effective_message.reply_text(MSG["list_tokens_usage"])
                return
            if not start_date:
                start_date = dt
            else:
                end_date = dt
    tokens = list_tokens(user_id=user_id, start_date=start_date, end_date=end_date)
    if not tokens:
        await update.effective_message.reply_text(MSG["list_tokens_none"])
        return
    lines = []
    for t in tokens:
        used = "✅" if t["used"] else "❌"
        user = f" ({t['user_id']})" if t["user_id"] else ""
        lines.append(
            f"{t['created_at'].strftime('%Y-%m-%d')} - {t['token']} - {t['duration']}d - {used}{user}"
        )
    await update.effective_message.reply_text("\n".join(lines))


@admin_only
async def set_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.effective_message.reply_text(MSG["set_rate_usage"])
        return
    try:
        days = int(context.args[0])
        amount = float(context.args[1])
    except ValueError:
        await update.effective_message.reply_text(MSG["set_rate_invalid"])
        return
    set_setting("rate_frequency", str(days))
    set_setting("rate_amount", str(amount))
    await update.effective_message.reply_text(
        MSG["set_rate_saved"].format(days=days, amount=amount)
    )


@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text(MSG["broadcast_usage"])
        return
    message = " ".join(context.args)
    sent = 0
    for sub in get_all_subscriptions():
        try:
            await context.bot.send_message(sub["user_id"], message)
            sent += 1
        except Exception as exc:
            logger.error("Error enviando a %s: %s", sub["user_id"], exc)
    await update.effective_message.reply_text(
        MSG["broadcast_sent"].format(sent=sent)
    )


@admin_only
async def gen_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.effective_message.reply_text(MSG["gen_link_usage"])
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text(MSG["gen_link_user_id_numeric"])
        return
    key = context.args[1]
    token, days = generate_token(key)
    add_subscription(user_id, token, days)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={token}"
    await update.effective_message.reply_text(
        MSG["gen_link_result"].format(link=link)
    )


@admin_only
async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.edit_message_text(
            MSG["admin_help"], parse_mode="HTML"
        )
    else:
        await update.effective_message.reply_html(MSG["admin_help"])


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar los comandos disponibles para cualquier usuario."""
    if update.callback_query:
        await update.callback_query.edit_message_text(
            MSG["help"], parse_mode="HTML"
        )
    else:
        await update.effective_message.reply_html(MSG["help"])


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.pop("awaiting_broadcast", False):
        message = update.effective_message.text
        sent = 0
        for sub in list_active_subscriptions():
            try:
                await context.bot.send_message(sub["user_id"], message)
                sent += 1
            except Exception as exc:
                logger.error("Error enviando a %s: %s", sub["user_id"], exc)
        keyboard = [[InlineKeyboardButton("Volver", callback_data="administracion")]]
        await update.effective_message.reply_text(
            MSG["broadcast_sent"].format(sent=sent),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif context.user_data.pop("awaiting_rate", False):
        parts = update.effective_message.text.split()
        keyboard = [[InlineKeyboardButton("Volver", callback_data="configuracion")]]
        if len(parts) != 2:
            await update.effective_message.reply_text(
                MSG["set_rate_invalid"], reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        try:
            days = int(parts[0])
            amount = float(parts[1])
        except ValueError:
            await update.effective_message.reply_text(
                MSG["set_rate_invalid"], reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        set_setting("rate_frequency", str(days))
        set_setting("rate_amount", str(amount))
        await update.effective_message.reply_text(
            MSG["set_rate_saved"].format(days=days, amount=amount),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif context.user_data.pop("awaiting_reminder", False):
        set_setting("reminder_message", update.effective_message.text)
        keyboard = [[InlineKeyboardButton("Volver", callback_data="configuracion")]]
        await update.effective_message.reply_text(
            MSG["reminder_saved"], reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif context.user_data.pop("awaiting_expired", False):
        set_setting("expiration_message", update.effective_message.text)
        keyboard = [[InlineKeyboardButton("Volver", callback_data="configuracion")]]
        await update.effective_message.reply_text(
            MSG["expired_saved"], reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = MSG["menu_prompt"]):
    """Mostrar el menu principal adecuando opciones según el rol del usuario."""
    if is_admin(update.effective_user.id):
        keyboard = [
            [InlineKeyboardButton("Configuración", callback_data="configuracion")],
            [InlineKeyboardButton("Administración", callback_data="administracion")],
        ]
    else:
        keyboard = [[InlineKeyboardButton("Solicitar token", callback_data="solicitar_token")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
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
        await query.answer(MSG["notify_admins"])
    elif data == "configuracion":
        keyboard = [
            [InlineKeyboardButton("Configurar tarifa", callback_data="set_tarifa")],
            [InlineKeyboardButton("Mensaje recordatorio", callback_data="set_recordatorio")],
            [InlineKeyboardButton("Mensaje expiración", callback_data="set_expiracion")],
            [InlineKeyboardButton("Volver", callback_data="volver")],
        ]
        await query.edit_message_text(
            MSG["config_menu"], reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "set_tarifa":
        context.user_data["awaiting_rate"] = True
        keyboard = [[InlineKeyboardButton("Cancelar", callback_data="configuracion")]]
        await query.edit_message_text(
            MSG["set_rate_prompt"], reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "set_recordatorio":
        context.user_data["awaiting_reminder"] = True
        keyboard = [[InlineKeyboardButton("Cancelar", callback_data="configuracion")]]
        await query.edit_message_text(
            MSG["set_reminder_prompt"], reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "set_expiracion":
        context.user_data["awaiting_expired"] = True
        keyboard = [[InlineKeyboardButton("Cancelar", callback_data="configuracion")]]
        await query.edit_message_text(
            MSG["set_expired_prompt"], reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "administracion":
        keyboard = [
            [InlineKeyboardButton("Estadísticas", callback_data="admin_stats")],
            [InlineKeyboardButton("Enviar broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("Tokens", callback_data="admin_tokens")],
            [InlineKeyboardButton("Generar token", callback_data="admin_gen_token")],
            [InlineKeyboardButton("Suscriptores", callback_data="admin_subs")],
            [InlineKeyboardButton("Volver", callback_data="volver")],
        ]
        await query.edit_message_text(
            MSG["admin_menu"], reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "admin_stats":
        await stats(update, context)
    elif data == "admin_broadcast":
        context.user_data["awaiting_broadcast"] = True
        keyboard = [[InlineKeyboardButton("Cancelar", callback_data="administracion")]]
        await query.edit_message_text(
            MSG["broadcast_prompt"], reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "admin_tokens":
        tokens = list_tokens()
        if not tokens:
            await query.edit_message_text(MSG["list_tokens_none"])
        else:
            lines = []
            for t in tokens:
                used = "✅" if t["used"] else "❌"
                user = f" ({t['user_id']})" if t["user_id"] else ""
                lines.append(
                    f"{t['created_at'].strftime('%Y-%m-%d')} - {t['token']} - {t['duration']}d - {used}{user}"
                )
            keyboard = [[InlineKeyboardButton("Volver", callback_data="administracion")]]
            await query.edit_message_text(
                "\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard)
            )
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
        await query.edit_message_text(
            MSG["token_duration_menu"], reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "admin_subs":
        subs = list_active_subscriptions()
        if not subs:
            await query.answer(MSG["list_subs_none"])
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
            await query.edit_message_text(
                "Suscriptores:", reply_markup=InlineKeyboardMarkup(keyboard)
            )
    elif data.startswith("sub_"):
        user_id = int(data.split("_")[1])
        sub = get_subscription(user_id)
        if not sub:
            await query.answer(MSG["subscriber_not_found"])
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
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("expulsar_"):
        user_id = int(data.split("_")[1])
        await context.bot.ban_chat_member(CHANNEL_ID, user_id)
        remove_subscription(user_id)
        await query.answer(MSG["user_removed"])
    elif data.startswith("token_"):
        key = data.split("_")[1]
        token, days = create_token(key)
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={token}"
        keyboard = [[InlineKeyboardButton("Volver", callback_data="administracion")]]
        await query.edit_message_text(
            MSG["token_generated"].format(link=link, days=days),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif data == "volver":
        await show_main_menu(update, context)
    elif data == "list_subs":
        await list_subs(update, context)
    elif data == "add_sub":
        await query.answer(MSG["add_sub_menu_usage"])
    elif data == "remove_sub":
        await query.answer(MSG["remove_sub_menu_usage"])
    elif data == "join":
        await query.answer(MSG["join_menu_usage"])




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
    text = MSG["stats_template"].format(
        total=total,
        joined_week=joined_week,
        left_week=left_week,
        reactions=reactions,
    )
    if update.callback_query:
        callback = (
            "administracion" if is_admin(update.effective_user.id) else "volver"
        )
        keyboard = [[InlineKeyboardButton("Volver", callback_data=callback)]]
        await update.callback_query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await update.effective_message.reply_html(text)


def main() -> None:
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("BOT_TOKEN y CHANNEL_ID deben estar definidos")

    init_db()
    init_config()

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.job_queue.scheduler.configure(timezone=pytz.utc)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set_reminder", set_reminder_message))
    application.add_handler(CommandHandler("set_expiration", set_expiration_message))
    application.add_handler(CommandHandler("gen_token", gen_token))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("add_sub", add_sub))
    application.add_handler(CommandHandler("remove_sub", remove_sub))
    application.add_handler(CommandHandler("list_subs", list_subs))
    application.add_handler(CommandHandler("list_tokens", list_tokens_cmd))
    application.add_handler(CommandHandler("set_rate", set_rate))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("gen_link", gen_link))
    application.add_handler(CommandHandler("admin", admin_help))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(menu_button))

    setup_subscription_monitor(application)

    application.run_polling()


if __name__ == "__main__":
    main()
