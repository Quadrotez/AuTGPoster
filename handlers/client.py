import os

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from dotenv import load_dotenv

from database import models

from filters.bot_filters import CallbackCommandFilter, WhitelistFilter

load_dotenv()

router = Router()

@router.message(Command("start"))
async def h_start(message: types.Message):
    user = models.User(message.chat.id)
    builder = InlineKeyboardBuilder()

    builder.button(text="Ru", callback_data="LANG ru")
    builder.button(text="En", callback_data="LANG en")

    await message.answer(await user.get_message("start"), reply_markup=builder.as_markup())


@router.message(WhitelistFilter(), F.text == os.environ["WHITELIST_PASSWORD"])
async def h_whitelist_password_entered(message: types.Message):
    user = models.User(message.chat.id)
    await message.answer(await user.get_message("whitelist_password_entered"))
    await user.init(message)


@router.callback_query(CallbackCommandFilter("LANG"))
async def h_lang_selected(data: types.CallbackQuery):
    user = models.User(data.from_user.id)

    await user.set_value("LANGUAGE", data.data.split()[1])

    await data.message.answer(await user.get_message("lang_selected"))


