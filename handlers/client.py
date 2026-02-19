import os

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from dotenv import load_dotenv

from database import models
from utils import aiogram_utils

from filters.bot_filters import (
    CallbackCommandFilter,
    WhitelistFilter,
    KeyboardCommandFilter,
    UserWhitelistedFilter,
)


load_dotenv()

router = Router()


class Form(StatesGroup):
    state_entering_channel_data = State()
    state_entering_schedule_data = State()
    channel_id = State()


@router.message(Command("start"))
async def h_start(message: types.Message):
    user = models.User(message.chat.id)
    builder = InlineKeyboardBuilder()

    if not await user.get("LANGUAGE"):
        builder.button(text="Ru", callback_data="LANG ru")
        builder.button(text="En", callback_data="LANG en")

        await message.answer(
            await user.get_message("first_start"), reply_markup=builder.as_markup()
        )
    else:
        keyboard = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[[types.KeyboardButton(text=await user.get_message("channels"))]],
        )

        await message.answer(await user.get_message("start"), reply_markup=keyboard)


@router.message(
    WhitelistFilter(),
    ~UserWhitelistedFilter(),
    F.text == os.environ["WHITELIST_PASSWORD"],
)
async def h_whitelist_password_entered(message: types.Message):
    user = models.User(message.chat.id)
    await message.answer(await user.get_message("whitelist_password_entered"))
    await user.init(message)
    await h_start(message)


@router.message(KeyboardCommandFilter("channels"))
async def h_channels(message: types.Message):
    builder = InlineKeyboardBuilder()

    user = models.User(message.chat.id)

    channels = models.Channels(message.chat.id)

    builder.button(text="Добавить", callback_data="ADD_CHANNEL")
    

    if not channels:
        await message.answer(
            await user.get_message("you_do_not_have_any_channels"),
            reply_markup=builder.as_markup(),
        )
        return

    for channel_id in await channels.get():
        channel = models.Channel(channel_id)
        builder.button(
            text=str(await channel.get("CHANNEL_NAME")),
            callback_data=f"MANAGE_CHANNEL {channel_id}",
        )
    await message.answer(
            await user.get_message("your_channels"),
            reply_markup=builder.as_markup(),
        )


@router.message(Form.state_entering_channel_data)
async def h_entering_channel_data(message: types.Message, state: FSMContext):
    user = models.User(message.chat.id)
    if message.forward_from:
        print("Короче это пересланное соо")
    elif message.text.isnumeric():
        if not message.text.startswith("-100"):
            channel_id = f"-100{message.text}"
        else:
            channel_id = message.text
        try:
            bot_member = await message.bot.get_chat_member(
                chat_id=channel_id, user_id=message.bot.id
            )
            if bot_member.status == "administrator":
                channel = models.Channel(channel_id)
                admins = await message.bot.get_chat_administrators(chat_id=channel_id)

                await channel.init(
                    set([admin.user.id for admin in admins]) - set([message.bot.id]),
                    await aiogram_utils.get_channel_owner(message.bot, channel_id),
                    (await message.bot.get_chat(channel_id)).title,
                )
                await message.answer(await user.get_message("channel_has_been_added"))

        except TelegramBadRequest:
            await message.answer(
                await user.get_message("bot_is_not_available_in_the_channel")
            )

    await state.clear()


@router.message(Form.state_entering_schedule_data)
async def h_entering_schedule_data(message: types.Message, state: FSMContext):
    user = models.User(message.chat.id)
    data = await state.get_data()
    channel_id = data["channel_id"]
    channel = models.Channel(channel_id=channel_id)

    await channel.set_value("SCHEDULE_DATA", message.text)
    await message.answer(await user.get_message("schedule_was_edited"))


@router.callback_query(CallbackCommandFilter("LANG"))
async def h_lang_selected(data: types.CallbackQuery):
    user = models.User(data.from_user.id)

    await user.set_value("LANGUAGE", data.data.split()[1])

    await data.message.answer(await user.get_message("lang_selected"))
    await h_start(data.message)


@router.callback_query(CallbackCommandFilter("ADD_CHANNEL"))
async def h_add_channel(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    await data.message.answer(await user.get_message("enter_data_to_add_channel"))
    await state.set_state(Form.state_entering_channel_data)


@router.callback_query(CallbackCommandFilter("MANAGE_CHANNEL"))
async def h_manage_channel(data: types.CallbackQuery):
    user = models.User(data.from_user.id)
    channel_id = data.data.split()[1]
    
    builder = InlineKeyboardBuilder()
    builder.button(text=await user.get_message("posts_settings"), callback_data=f"POSTS_SETTINGS {channel_id}")

    await data.message.answer(await user.get_message("enter_what_you_want_to_change_in_your_channel"), reply_markup=builder.as_markup())


@router.callback_query(CallbackCommandFilter("POSTS_SETTINGS"))
async def h_posts_settings(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    channel_id = data.data.split()[1]

    builder = InlineKeyboardBuilder()

    builder.button(text=await user.get_message("set_schedule"), callback_data=f"SCHEDULE_SETTINGS {channel_id}")

    await data.message.answer(await user.get_message("posts_settings_menu"), reply_markup=builder.as_markup())
    

@router.callback_query(CallbackCommandFilter("schedule_settings"))
async def h_schedule_settings(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    channel_id = data.data.split()[1]

    await data.message.answer(await user.get_message("enter_schedule_data"))
    await state.set_data({"channel_id": channel_id})
    await state.set_state(Form.state_entering_schedule_data)
    