import asyncio

from bot import bot, dp
from database import init_db
from tools.subscription_monitor import monitor_subscriptions
from handlers.user import start_router
from handlers.admin import (
    token_router,
    users_router,
    broadcast_router,
    config_router,
)


async def main() -> None:
    await init_db()
    asyncio.create_task(monitor_subscriptions())
    dp.include_router(start_router)
    dp.include_router(token_router)
    dp.include_router(users_router)
    dp.include_router(broadcast_router)
    dp.include_router(config_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
