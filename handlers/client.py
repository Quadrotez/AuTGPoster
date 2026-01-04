import os

from aiogram import Router, types, F
from aiogram.filters import Command

from dotenv import load_dotenv

from database import models
from filters import user_filters, bot_filters

load_dotenv()

router = Router()

@router.message(Command("start"))
async def h_start(message: types.Message):
    user = models.User(message.chat.id)
    await message.answer(await user.get_message("start"))


@router.message(bot_filters.WhitelistFilter(), F.text == os.environ["WHITELIST_PASSWORD"])
async def h_whitelist_password_entered(message: types.Message):
    user = models.User(message.chat.id)
    await message.answer(await user.get_message("whitelist_password_entered"))
    await user.init(message)

