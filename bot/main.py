import asyncio
import logging
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .messages import MESSAGES as MSG
from .handlers.admin.config_messages import router as config_router, is_admin
from .services.subscription_monitor import subscription_monitor
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
    use_token,
)
from .token_manager import generate_token, create_token
from .utils.config import init_config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

dp = Dispatcher()
dp.include_router(config_router)

# Simple per-user state storage
_states: dict[int, dict[str, bool]] = {}


def set_state(user_id: int, key: str) -> None:
    _states.setdefault(user_id, {})[key] = True


def pop_state(user_id: int, key: str) -> bool:
    return _states.get(user_id, {}).pop(key, False)


@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject) -> None:
    if command.args:
        token = command.args.strip()
        duration = use_token(token)
        if not duration:
            await message.answer(MSG["join_token_invalid"])
            return
        add_subscription(message.from_user.id, token, duration)
        invite = await message.bot.create_chat_invite_link(CHANNEL_ID, member_limit=1)
        await message.answer(MSG["join_success"].format(link=invite.invite_link))
        return
    await show_main_menu(message)


@dp.message(Command("gen_token"))
async def gen_token_cmd(message: types.Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(MSG["access_denied"])
        return
    args = command.args.split() if command.args else []
    if len(args) != 1:
        await message.answer(MSG["gen_token_usage"])
        return
    key = args[0]
    token, days = create_token(key)
    me = await message.bot.me()
    link = f"https://t.me/{me.username}?start={token}"
    await message.answer(MSG["gen_token_result"].format(link=link, days=days))


@dp.message(Command("join"))
async def join_cmd(message: types.Message, command: CommandObject) -> None:
    args = command.args.split() if command.args else []
    if len(args) != 1:
        await message.answer(MSG["join_token_missing"])
        return
    token = args[0]
    duration = use_token(token)
    if not duration:
        await message.answer(MSG["join_token_invalid"])
        return
    add_subscription(message.from_user.id, token, duration)
    invite = await message.bot.create_chat_invite_link(CHANNEL_ID, member_limit=1)
    await message.answer(MSG["join_success"].format(link=invite.invite_link))


@dp.message(Command("add_sub"))
async def add_sub_cmd(message: types.Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(MSG["access_denied"])
        return
    args = command.args.split() if command.args else []
    if len(args) != 2:
        await message.answer(MSG["add_sub_usage"])
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await message.answer(MSG["add_sub_user_id_numeric"])
        return
    key = args[1]
    token, days = generate_token(key)
    add_subscription(user_id, token, days)
    await message.answer(MSG["add_sub_success"].format(user_id=user_id, token=token))


@dp.message(Command("remove_sub"))
async def remove_sub_cmd(message: types.Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(MSG["access_denied"])
        return
    args = command.args.split() if command.args else []
    if len(args) != 1:
        await message.answer(MSG["remove_sub_usage"])
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await message.answer(MSG["remove_sub_user_id_numeric"])
        return
    remove_subscription(user_id)
    await message.answer(MSG["remove_sub_success"])


@dp.message(Command("list_subs"))
async def list_subs_cmd(message: types.Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(MSG["access_denied"])
        return
    subs = list_active_subscriptions()
    if not subs:
        await message.answer(MSG["list_subs_none"])
        return
    lines = [f"{s['user_id']} - {s['start_date'].strftime('%Y-%m-%d')}" for s in subs]
    await message.answer("\n".join(lines))


@dp.message(Command("list_tokens"))
async def list_tokens_cmd(message: types.Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(MSG["access_denied"])
        return
    args = command.args.split() if command.args else []
    user_id = None
    start_date = None
    end_date = None
    for arg in args:
        if arg.isdigit():
            user_id = int(arg)
        else:
            try:
                dt = datetime.fromisoformat(arg)
            except ValueError:
                await message.answer(MSG["list_tokens_usage"])
                return
            if not start_date:
                start_date = dt
            else:
                end_date = dt
    tokens = list_tokens(user_id=user_id, start_date=start_date, end_date=end_date)
    if not tokens:
        await message.answer(MSG["list_tokens_none"])
        return
    lines = []
    for t in tokens:
        used = "✅" if t["used"] else "❌"
        user = f" ({t['user_id']})" if t["user_id"] else ""
        lines.append(
            f"{t['created_at'].strftime('%Y-%m-%d')} - {t['token']} - {t['duration']}d - {used}{user}"
        )
    await message.answer("\n".join(lines))


@dp.message(Command("set_rate"))
async def set_rate_cmd(message: types.Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(MSG["access_denied"])
        return
    args = command.args.split() if command.args else []
    if len(args) != 2:
        await message.answer(MSG["set_rate_usage"])
        return
    try:
        days = int(args[0])
        amount = float(args[1])
    except ValueError:
        await message.answer(MSG["set_rate_invalid"])
        return
    set_setting("rate_frequency", str(days))
    set_setting("rate_amount", str(amount))
    await message.answer(MSG["set_rate_saved"].format(days=days, amount=amount))


@dp.message(Command("broadcast"))
async def broadcast_cmd(message: types.Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(MSG["access_denied"])
        return
    if not command.args:
        await message.answer(MSG["broadcast_usage"])
        return
    text = command.args
    sent = 0
    for sub in get_all_subscriptions():
        try:
            await message.bot.send_message(sub["user_id"], text)
            sent += 1
        except Exception as exc:
            logger.error("Error enviando a %s: %s", sub["user_id"], exc)
    await message.answer(MSG["broadcast_sent"].format(sent=sent))


@dp.message(Command("gen_link"))
async def gen_link_cmd(message: types.Message, command: CommandObject) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(MSG["access_denied"])
        return
    args = command.args.split() if command.args else []
    if len(args) != 2:
        await message.answer(MSG["gen_link_usage"])
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await message.answer(MSG["gen_link_user_id_numeric"])
        return
    key = args[1]
    token, days = generate_token(key)
    add_subscription(user_id, token, days)
    me = await message.bot.me()
    link = f"https://t.me/{me.username}?start={token}"
    await message.answer(MSG["gen_link_result"].format(link=link))


@dp.message(Command("admin"))
async def admin_help_cmd(message: types.Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(MSG["access_denied"])
        return
    await message.answer(MSG["admin_help"], parse_mode="HTML")


@dp.message(Command("help"))
async def help_cmd(message: types.Message) -> None:
    await message.answer(MSG["help"], parse_mode="HTML")


@dp.message(Command("menu"))
async def menu_cmd(message: types.Message) -> None:
    await show_main_menu(message)


@dp.message()
async def handle_message(message: types.Message) -> None:
    if pop_state(message.from_user.id, "awaiting_broadcast"):
        text = message.text
        sent = 0
        for sub in list_active_subscriptions():
            try:
                await message.bot.send_message(sub["user_id"], text)
                sent += 1
            except Exception as exc:
                logger.error("Error enviando a %s: %s", sub["user_id"], exc)
        keyboard = [[InlineKeyboardButton(text="Volver", callback_data="administracion")]]
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(MSG["broadcast_sent"].format(sent=sent), reply_markup=markup)
    elif pop_state(message.from_user.id, "awaiting_rate"):
        parts = message.text.split()
        keyboard = [[InlineKeyboardButton(text="Volver", callback_data="configuracion")]]
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        if len(parts) != 2:
            await message.answer(MSG["set_rate_invalid"], reply_markup=markup)
            return
        try:
            days = int(parts[0])
            amount = float(parts[1])
        except ValueError:
            await message.answer(MSG["set_rate_invalid"], reply_markup=markup)
            return
        set_setting("rate_frequency", str(days))
        set_setting("rate_amount", str(amount))
        await message.answer(
            MSG["set_rate_saved"].format(days=days, amount=amount), reply_markup=markup
        )
    elif pop_state(message.from_user.id, "awaiting_reminder"):
        set_setting("reminder_message", message.text)
        keyboard = [[InlineKeyboardButton(text="Volver", callback_data="configuracion")]]
        await message.answer(MSG["reminder_saved"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    elif pop_state(message.from_user.id, "awaiting_expired"):
        set_setting("expiration_message", message.text)
        keyboard = [[InlineKeyboardButton(text="Volver", callback_data="configuracion")]]
        await message.answer(MSG["expired_saved"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@dp.callback_query()
async def menu_button(query: types.CallbackQuery) -> None:
    data = query.data
    await query.answer()
    if data == "help":
        await query.message.edit_text(MSG["help"], parse_mode="HTML")
    elif data == "stats":
        await stats(query)
    elif data == "solicitar_token":
        for admin_id in ADMIN_IDS:
            try:
                await query.bot.send_message(
                    admin_id, f"El usuario {query.from_user.id} solicita un token"
                )
            except Exception as exc:
                logger.error("No se pudo notificar a %s: %s", admin_id, exc)
        await query.answer(MSG["notify_admins"])
    elif data == "configuracion":
        keyboard = [
            [InlineKeyboardButton(text="Configurar tarifa", callback_data="set_tarifa")],
            [InlineKeyboardButton(text="Mensaje recordatorio", callback_data="set_recordatorio")],
            [InlineKeyboardButton(text="Mensaje expiración", callback_data="set_expiracion")],
            [InlineKeyboardButton(text="Volver", callback_data="volver")],
        ]
        await query.message.edit_text(
            MSG["config_menu"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    elif data == "set_tarifa":
        set_state(query.from_user.id, "awaiting_rate")
        keyboard = [[InlineKeyboardButton(text="Cancelar", callback_data="configuracion")]]
        await query.message.edit_text(
            MSG["set_rate_prompt"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    elif data == "set_recordatorio":
        set_state(query.from_user.id, "awaiting_reminder")
        keyboard = [[InlineKeyboardButton(text="Cancelar", callback_data="configuracion")]]
        await query.message.edit_text(
            MSG["set_reminder_prompt"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    elif data == "set_expiracion":
        set_state(query.from_user.id, "awaiting_expired")
        keyboard = [[InlineKeyboardButton(text="Cancelar", callback_data="configuracion")]]
        await query.message.edit_text(
            MSG["set_expired_prompt"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    elif data == "administracion":
        keyboard = [
            [InlineKeyboardButton(text="Estadísticas", callback_data="admin_stats")],
            [InlineKeyboardButton(text="Enviar broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="Tokens", callback_data="admin_tokens")],
            [InlineKeyboardButton(text="Generar token", callback_data="admin_gen_token")],
            [InlineKeyboardButton(text="Suscriptores", callback_data="admin_subs")],
            [InlineKeyboardButton(text="Volver", callback_data="volver")],
        ]
        await query.message.edit_text(
            MSG["admin_menu"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    elif data == "admin_stats":
        await stats(query)
    elif data == "admin_broadcast":
        set_state(query.from_user.id, "awaiting_broadcast")
        keyboard = [[InlineKeyboardButton(text="Cancelar", callback_data="administracion")]]
        await query.message.edit_text(
            MSG["broadcast_prompt"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    elif data == "admin_tokens":
        tokens = list_tokens()
        if not tokens:
            await query.message.edit_text(MSG["list_tokens_none"])
        else:
            lines = []
            for t in tokens:
                used = "✅" if t["used"] else "❌"
                user = f" ({t['user_id']})" if t["user_id"] else ""
                lines.append(
                    f"{t['created_at'].strftime('%Y-%m-%d')} - {t['token']} - {t['duration']}d - {used}{user}"
                )
            keyboard = [[InlineKeyboardButton(text="Volver", callback_data="administracion")]]
            await query.message.edit_text(
                "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
    elif data == "admin_gen_token":
        keyboard = [
            [InlineKeyboardButton(text="1 día", callback_data="token_1d"), InlineKeyboardButton(text="1 semana", callback_data="token_1w")],
            [InlineKeyboardButton(text="2 semanas", callback_data="token_2w"), InlineKeyboardButton(text="1 mes", callback_data="token_1m")],
            [InlineKeyboardButton(text="Permanente", callback_data="token_forever")],
            [InlineKeyboardButton(text="Volver", callback_data="administracion")],
        ]
        await query.message.edit_text(
            MSG["token_duration_menu"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    elif data == "admin_subs":
        subs = list_active_subscriptions()
        if not subs:
            await query.answer(MSG["list_subs_none"])
        else:
            keyboard = [
                [InlineKeyboardButton(text=str(s["user_id"]), callback_data=f"sub_{s['user_id']}")]
                for s in subs
            ]
            keyboard.append([InlineKeyboardButton(text="Volver", callback_data="administracion")])
            await query.message.edit_text(
                "Suscriptores:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
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
                [InlineKeyboardButton(text="Expulsar", callback_data=f"expulsar_{user_id}")],
                [InlineKeyboardButton(text="Volver", callback_data="admin_subs")],
            ]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    elif data.startswith("expulsar_"):
        user_id = int(data.split("_")[1])
        await query.bot.ban_chat_member(CHANNEL_ID, user_id)
        remove_subscription(user_id)
        await query.answer(MSG["user_removed"])
    elif data.startswith("token_"):
        key = data.split("_")[1]
        token, days = create_token(key)
        me = await query.bot.me()
        link = f"https://t.me/{me.username}?start={token}"
        keyboard = [[InlineKeyboardButton(text="Volver", callback_data="administracion")]]
        await query.message.edit_text(
            MSG["token_generated"].format(link=link, days=days),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
    elif data == "volver":
        await show_main_menu(query)
    elif data == "list_subs":
        await list_subs_cmd(query.message)
    elif data == "add_sub":
        await query.answer(MSG["add_sub_menu_usage"])
    elif data == "remove_sub":
        await query.answer(MSG["remove_sub_menu_usage"])
    elif data == "join":
        await query.answer(MSG["join_menu_usage"])


async def stats(event: types.Message | types.CallbackQuery) -> None:
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
    reactions = 0
    text = MSG["stats_template"].format(
        total=total,
        joined_week=joined_week,
        left_week=left_week,
        reactions=reactions,
    )
    if isinstance(event, types.CallbackQuery):
        callback = "administracion" if is_admin(event.from_user.id) else "volver"
        keyboard = [[InlineKeyboardButton(text="Volver", callback_data=callback)]]
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    else:
        await event.answer(text, parse_mode="HTML")


async def show_main_menu(target: types.Message | types.CallbackQuery, text: str = MSG["menu_prompt"]) -> None:
    if is_admin(target.from_user.id):
        keyboard = [
            [InlineKeyboardButton(text="Configuración", callback_data="configuracion")],
            [InlineKeyboardButton(text="Administración", callback_data="administracion")],
        ]
    else:
        keyboard = [[InlineKeyboardButton(text="Solicitar token", callback_data="solicitar_token")]]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    if isinstance(target, types.CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


async def main() -> None:
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("BOT_TOKEN y CHANNEL_ID deben estar definidos")

    init_db()
    init_config()

    bot = Bot(BOT_TOKEN)

    asyncio.create_task(subscription_monitor(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

