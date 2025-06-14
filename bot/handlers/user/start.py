from datetime import datetime, timedelta
import os

from aiogram import Router, types
from aiogram.filters import Command, CommandObject

from ...database import (
    use_token,
    add_user_subscription,
    get_user_subscription,
)
from ..admin.config_messages import is_admin

CHANNEL_ID = os.getenv("CHANNEL_ID")

router = Router()


@router.message(Command("start"))
async def start(message: types.Message, command: CommandObject) -> None:
    """Handle /start command with optional token."""

    token = command.args
    user = message.from_user

    if token:
        duration = use_token(token)
        if not duration:
            await message.answer("Invalid or expired token.")
            return

        expiration = datetime.utcnow() + timedelta(days=duration)
        add_user_subscription(
            user.id,
            user.username or "",
            user.full_name or "",
            expiration,
        )

        invite = await message.bot.create_chat_invite_link(
            CHANNEL_ID, member_limit=1
        )
        await message.answer(
            f"Welcome! Join here: {invite.invite_link}"
        )
        return

    # No token provided
    if is_admin(user.id):
        keyboard = [
            [types.InlineKeyboardButton(text="Configuration", callback_data="configuracion")],
            [types.InlineKeyboardButton(text="Administration", callback_data="administracion")],
        ]
        await message.answer(
            "Admin menu:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
        return

    sub = get_user_subscription(user.id)
    if sub:
        keyboard = [
            [types.InlineKeyboardButton(text="Profile", callback_data="profile")],
            [
                types.InlineKeyboardButton(
                    text="Check Subscription", callback_data="check_subscription"
                )
            ],
            [types.InlineKeyboardButton(text="Help", callback_data="help")],
        ]
        await message.answer(
            "Subscriber menu:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
    else:
        await message.answer(
            "You are not subscribed. Please contact support."
        )

