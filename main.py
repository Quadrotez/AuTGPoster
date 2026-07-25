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
from utils import aiogram_utils

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
        now_iso = utc_now.strftime("%Y-%m-%dT%H:%M:00")

        channels = await db.execute("SELECT CHAT_ID FROM CHANNELS", fetch=True, force_list=True)

        for channel_id in channels:
            channel = models.Channel(channel_id)
            schedule_data = await channel.get("SCHEDULE_DATA")

            if schedule_data and schedule_data != "{}":
                try:
                    schedule = json.loads(schedule_data)
                except (json.JSONDecodeError, TypeError):
                    schedule = {}

                if schedule:
                    owner_id = await channel.get("OWNER_ID")
                    tz_offset = await db.execute("SELECT TIMEZONE FROM USERS WHERE CHAT_ID = ?", (owner_id,), fetch=True) or 0
                    local_now = utc_now + timedelta(hours=float(tz_offset))

                    weekday = local_now.strftime("%A").lower()
                    current_time = local_now.strftime("%H:%M")

                    if current_time in schedule.get(weekday, []):
                        queue = models.PostsQueue(channel_id)
                        post = await queue.get_next()

                        if post:
                            post_id, from_chat_id, message_id, pin, unpin_at, delete_at, buttons = post
                            await aiogram_utils.send_post(bot, channel_id, from_chat_id, message_id, bool(pin), unpin_at, delete_at, buttons)
                            await queue.remove(post_id)

            queue = models.PostsQueue(channel_id)
            due_post = await queue.get_due(now_iso)
            if due_post:
                post_id, from_chat_id, message_id, pin, unpin_at, delete_at, buttons = due_post
                await aiogram_utils.send_post(bot, channel_id, from_chat_id, message_id, bool(pin), unpin_at, delete_at, buttons)
                await queue.remove(post_id)

        unpin_ids = await db.execute(
            "SELECT ID FROM SENT_POSTS WHERE UNPIN_AT IS NOT NULL AND UNPIN_AT <= ?",
            (now_iso,), fetch=True, force_list=True
        )
        for post_id in unpin_ids:
            post_data = await db.execute("SELECT CHANNEL_ID, MESSAGE_ID FROM SENT_POSTS WHERE ID = ?", (post_id,), fetch=True)
            if not post_data:
                continue
            ch_id, msg_id = post_data
            try:
                await bot.unpin_chat_message(chat_id=ch_id, message_id=msg_id)
            except Exception:
                pass
            await db.execute("UPDATE SENT_POSTS SET UNPIN_AT = NULL WHERE ID = ?", (post_id,))
            has_delete = await db.execute("SELECT DELETE_AT FROM SENT_POSTS WHERE ID = ?", (post_id,), fetch=True)
            if not has_delete:
                await db.execute("DELETE FROM SENT_POSTS WHERE ID = ?", (post_id,))

        delete_ids = await db.execute(
            "SELECT ID FROM SENT_POSTS WHERE DELETE_AT IS NOT NULL AND DELETE_AT <= ?",
            (now_iso,), fetch=True, force_list=True
        )
        for post_id in delete_ids:
            post_data = await db.execute("SELECT CHANNEL_ID, MESSAGE_ID FROM SENT_POSTS WHERE ID = ?", (post_id,), fetch=True)
            if not post_data:
                continue
            ch_id, msg_id = post_data
            try:
                await bot.delete_message(chat_id=ch_id, message_id=msg_id)
            except Exception:
                pass
            await db.execute("DELETE FROM SENT_POSTS WHERE ID = ?", (post_id,))


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
