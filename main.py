import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from aiogram.client.session.aiohttp import AiohttpSession

from database import db
from middlewares import default_middlewares
from handlers import client

from aiogram import Bot, Dispatcher

load_dotenv()

if os.getenv("PROXY"):
    session = AiohttpSession(proxy=os.environ["PROXY"])
else:
    session = None

bot, dp = Bot(os.environ["TELEGRAM_BOT_TOKEN"], session=session), Dispatcher()


async def main():
    await db.init_database()
    logging.basicConfig(level=logging.INFO)
    print(datetime.now().strftime(r"Текущая дата: %d.%m.%Y"))

    dp.message.middleware(default_middlewares.InitUserMiddleware())
    dp.include_routers(client.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
