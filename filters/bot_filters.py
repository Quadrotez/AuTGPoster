import os

from aiogram import types
from aiogram.filters import BaseFilter

from dotenv import load_dotenv

load_dotenv()

class WhitelistFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return os.environ["WHITELIST"] == "1"
