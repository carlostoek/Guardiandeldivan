import asyncio
from datetime import datetime

from aiogram import Bot

from ..database import (
    get_all_user_subscriptions,
    mark_user_reminded,
    mark_user_expired_notified,
)
from ..utils.config import load_config


def _build_message(template: str, username: str, expiration_date: datetime) -> str:
    return template.format(
        username=username,
        expiration_date=expiration_date.strftime("%Y-%m-%d"),
    )


async def _check_subscriptions(bot: Bot) -> None:
    now = datetime.utcnow()
    reminder_template = load_config(
        "reminder_message",
        "Hola {username}, tu suscripción expira el {expiration_date}",
    )
    expiration_template = load_config(
        "expiration_message",
        "Hola {username}, tu suscripción ha expirado el {expiration_date}",
    )
    for sub in get_all_user_subscriptions():
        days_left = (sub["expiration_date"] - now).days
        if days_left == 1 and not sub["reminded"]:
            text = _build_message(
                reminder_template,
                sub["username"] or sub["full_name"],
                sub["expiration_date"],
            )
            try:
                await bot.send_message(sub["user_id"], text)
                mark_user_reminded(sub["user_id"])
            except Exception:
                pass
        elif days_left <= 0 and not sub["expired_notified"]:
            text = _build_message(
                expiration_template,
                sub["username"] or sub["full_name"],
                sub["expiration_date"],
            )
            try:
                await bot.send_message(sub["user_id"], text)
                mark_user_expired_notified(sub["user_id"])
            except Exception:
                pass


async def subscription_monitor(bot: Bot) -> None:
    """Background task that checks subscriptions once a day."""
    while True:
        await _check_subscriptions(bot)
        await asyncio.sleep(86400)

