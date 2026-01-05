import os

from aiogram.types import CallbackQuery, Message
from aiogram.filters import BaseFilter

from dotenv import load_dotenv

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
