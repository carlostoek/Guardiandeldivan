from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

__all__ = ["ADMIN_MENU_KB"]

ADMIN_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Generar Token", callback_data="admin_gen_token")],
        [InlineKeyboardButton(text="Usuarios", callback_data="admin_users")],
        [InlineKeyboardButton(text="Configurar mensajes", callback_data="admin_config_messages")],
        [InlineKeyboardButton(text="Estadísticas", callback_data="admin_stats")],
    ]
)

