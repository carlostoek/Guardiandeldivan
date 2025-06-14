from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import get_settings

settings = get_settings()

bot = Bot(settings.bot_token, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())
