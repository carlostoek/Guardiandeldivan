from aiogram import Router
from .start import router as start_router


def register_handlers() -> list[Router]:
    return [start_router]
