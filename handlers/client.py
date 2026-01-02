from aiogram import Router, types
from aiogram.filters import Command


router = Router()

@router.message(Command("start"))
async def h_start(message: types.Message):
    await message.answer("Hello")
