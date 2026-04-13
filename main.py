import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from aiogram.client.session.aiohttp import AiohttpSession

from database import db, models
from middlewares import default_middlewares
from handlers import client

from aiogram import Bot, Dispatcher

load_dotenv()

if os.getenv("PROXY"):
    session = AiohttpSession(proxy=os.environ["PROXY"])
else:
    session = None

bot, dp = Bot(os.environ["TELEGRAM_BOT_TOKEN"], session=session), Dispatcher()


async def run_scheduler():
    while True:
        await asyncio.sleep(60)

        utc_now = datetime.now(timezone.utc)

        channels = await db.execute("SELECT CHAT_ID FROM CHANNELS", fetch=True, force_list=True)

        for channel_id in channels:
            channel = models.Channel(channel_id)
            schedule_data = await channel.get("SCHEDULE_DATA")

            if not schedule_data or schedule_data == "{}":
                continue

            try:
                schedule = json.loads(schedule_data)
            except (json.JSONDecodeError, TypeError):
                continue

            owner_id = await channel.get("OWNER_ID")
            tz_offset = await db.execute("SELECT TIMEZONE FROM USERS WHERE CHAT_ID = ?", (owner_id,), fetch=True) or 0
            local_now = utc_now + timedelta(hours=float(tz_offset))

            weekday = local_now.strftime("%A").lower()
            current_time = local_now.strftime("%H:%M")

            if current_time not in schedule.get(weekday, []):
                continue

            queue = models.PostsQueue(channel_id)
            post = await queue.get_next()

            if not post:
                continue

            post_id, from_chat_id, message_id = post
            await bot.copy_message(chat_id=channel_id, from_chat_id=from_chat_id, message_id=message_id)
            await queue.remove(post_id)


async def main():
    await db.init_database()
    logging.basicConfig(level=logging.INFO)
    print(datetime.now().strftime(r"Текущая дата: %d.%m.%Y"))

    dp.message.middleware(default_middlewares.InitUserMiddleware())
    dp.callback_query.middleware(default_middlewares.InitUserMiddleware())
    dp.include_routers(client.router)

    asyncio.create_task(run_scheduler())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
