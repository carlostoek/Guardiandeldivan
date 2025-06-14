import asyncio

from bot import bot, dp
from database import init_db
from handlers.user import start_router
from handlers.admin import token_router, broadcast_router


async def main() -> None:
    await init_db()
    dp.include_router(start_router)
    dp.include_router(token_router)
    dp.include_router(broadcast_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
