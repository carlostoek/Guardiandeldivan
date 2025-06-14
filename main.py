import asyncio

from bot import bot, dp
from handlers import register_handlers


async def main() -> None:
    for router in register_handlers():
        dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
