import os

from aiogram.types import CallbackQuery, Message
from aiogram.filters import BaseFilter

from dotenv import load_dotenv

from database import models

load_dotenv()

class WhitelistFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:

        return os.environ["WHITELIST"] == "1"


class CallbackCommandFilter(BaseFilter):
    def __init__(self, command: str) -> None:
        self.command = command

    async def __call__(self, query: CallbackQuery) -> bool:
        query_command = str(query.data).split()[0]
        return str(query_command).upper() == self.command.upper()


class KeyboardCommandFilter(BaseFilter):
    def __init__(self, command: str, get_from_language: bool = True) -> None:
        self.get_from_language = get_from_language
        self.command = command

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False

        if self.get_from_language:
            user = models.User(message.chat.id)

            target_command = await user.get_message(self.command)

        command = message.text

        return command.upper() == target_command.upper()


class UserWhitelistedFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        user = models.User(message.chat.id)
        return await user.exists()

