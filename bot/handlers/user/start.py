from datetime import datetime, timedelta
import os

from telegram import Update
from telegram.ext import ContextTypes

from ...database import use_token, add_user_subscription

CHANNEL_ID = os.getenv("CHANNEL_ID")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start <token> command."""
    args = context.args
    if args:
        token = args[0]
        duration = use_token(token)
        if not duration:
            await update.effective_message.reply_text("❌ Token inválido")
            return
        user = update.effective_user
        expiration = datetime.utcnow() + timedelta(days=duration)
        add_user_subscription(
            user.id,
            user.username or "",
            user.full_name or "",
            expiration,
        )
        invite = await context.bot.create_chat_invite_link(
            CHANNEL_ID, member_limit=1
        )
        await update.effective_message.reply_text(
            f"✅ Registro exitoso. Únete aquí: {invite.invite_link}"
        )
    else:
        await update.effective_message.reply_text(
            "Envía /start <token> para activar tu suscripción"
        )

