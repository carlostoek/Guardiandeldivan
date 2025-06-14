from __future__ import annotations

from aiogram import Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from services.config_service import get_pricing
from services.subscription_service import list_active_subscriptions, remove_subscription
from services.token_service import generate_token
from bot import messages
from config import settings

router = Router()
__all__ = ["ADMIN_MENU_KB", "router"]

ADMIN_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Ajustes", callback_data="admin_settings")],
        [InlineKeyboardButton(text="🛠️ Administración", callback_data="admin_tools")],
    ]
)

SETTINGS_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Definir precio", callback_data="settings_set_price")],
        [InlineKeyboardButton(text="Volver", callback_data="back_admin_menu")],
    ]
)

ADMINISTRATION_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Estadísticas", callback_data="admin_stats")],
        [InlineKeyboardButton(text="Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="Generar enlace", callback_data="admin_gen_link")],
        [InlineKeyboardButton(text="Suscriptores", callback_data="admin_list_subs")],
        [InlineKeyboardButton(text="Volver", callback_data="back_admin_menu")],
    ]
)


@router.callback_query(lambda c: c.data == "admin_settings")
async def cb_settings(callback: CallbackQuery) -> None:
    pricing = await get_pricing()
    text = messages.SETTINGS_MENU
    if pricing:
        text += "\n" + messages.CURRENT_PRICE.format(period=pricing[0], amount=pricing[1])
    await callback.message.edit_text(text, reply_markup=SETTINGS_MENU_KB)
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_tools")
async def cb_tools(callback: CallbackQuery) -> None:
    await callback.message.edit_text(messages.ADMINISTRATION_MENU, reply_markup=ADMINISTRATION_MENU_KB)
    await callback.answer()


@router.callback_query(lambda c: c.data == "back_admin_menu")
async def cb_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text(messages.ADMIN_MENU, reply_markup=ADMIN_MENU_KB)
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_stats")
async def cb_stats(callback: CallbackQuery) -> None:
    subs = await list_active_subscriptions()
    active = len(subs)
    pricing = await get_pricing()
    amount = float(pricing[1]) if pricing else 0
    revenue = active * amount
    text = messages.STATS_OVERVIEW.format(active=active, renewals=0, revenue=revenue)
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_broadcast")
async def cb_broadcast(callback: CallbackQuery) -> None:
    await callback.message.answer(messages.BROADCAST_INSTRUCTIONS)
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_gen_link")
async def cb_gen_link(callback: CallbackQuery) -> None:
    token = await generate_token(7)
    link = f"https://t.me/{settings.BOT_TOKEN.split(':')[0]}?start={token}"
    await callback.message.answer(messages.ACCESS_LINK.format(link=link))
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_list_subs")
async def cb_list_subs(callback: CallbackQuery) -> None:
    subs = await list_active_subscriptions()
    for sub in subs:
        days = (sub.end_date - sub.start_date).days
        text = messages.SUBSCRIBER_INFO.format(
            user_id=sub.user_id,
            start=sub.start_date.date(),
            end=sub.end_date.date(),
            days=days,
            renewals=0,
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Eliminar", callback_data=f"remove_user:{sub.user_id}")]]
        )
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("remove_user:"))
async def cb_remove(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split(":", 1)[1])
    await remove_subscription(user_id)
    await callback.message.answer(messages.USER_REMOVED.format(user_id=user_id))
    await callback.answer()
