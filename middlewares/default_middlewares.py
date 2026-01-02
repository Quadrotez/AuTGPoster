from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Awaitable, Dict, Any

from database import models
from dotenv import load_dotenv

import os

load_dotenv()

class InitUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:

        if event.text:
            user = models.User(event.chat.id)

            if not await user.exists():
                if int(os.environ["WHITELIST"]):
                    if event.text != os.environ["WHITELIST_PASSWORD"]:
                        await event.answer("В боте включён WhiteList! Для работы с ботом введите пароль или обратитесь к администратору")
                    else:
                        await event.answer("Был введён пароль вайтлиста!")
                        await user.init(event)

            else:
                return await handler(event, data)