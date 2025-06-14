from datetime import datetime, timedelta

from telegram.ext import ContextTypes, Application

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


async def _check_subscriptions(context: ContextTypes.DEFAULT_TYPE):
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
                reminder_template, sub["username"] or sub["full_name"], sub["expiration_date"]
            )
            try:
                await context.bot.send_message(sub["user_id"], text)
                mark_user_reminded(sub["user_id"])
            except Exception:
                pass
        elif days_left <= 0 and not sub["expired_notified"]:
            text = _build_message(
                expiration_template, sub["username"] or sub["full_name"], sub["expiration_date"]
            )
            try:
                await context.bot.send_message(sub["user_id"], text)
                mark_user_expired_notified(sub["user_id"])
            except Exception:
                pass


def setup_subscription_monitor(application: Application):
    application.job_queue.run_repeating(_check_subscriptions, interval=86400, first=0)

