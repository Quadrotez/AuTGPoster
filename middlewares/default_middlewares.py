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
        user = models.User(event.from_user.id)
        
        if not await user.exists() and (int(os.environ["WHITELIST"]) and (type(event) is not Message or event.text != os.environ["WHITELIST_PASSWORD"])):
            await event.answer(await user.get_message("you_are_not_whitelisted_notification"))
        else:
            return await handler(event, data)
                

                