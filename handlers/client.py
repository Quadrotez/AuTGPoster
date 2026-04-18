import os
from datetime import datetime

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from dotenv import load_dotenv

from database import models
from utils import aiogram_utils, time_utils

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
    state_waiting_for_post = State()
    state_post_settings = State()
    state_entering_unpin_time = State()
    state_entering_delete_time = State()
    state_entering_buttons = State()
    state_choosing_publish = State()


async def _post_settings_markup(user: models.User, data: dict) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if data.get("pin"):
        if data.get("unpin_at_display"):
            pin_text = (await user.get_message("post_pin_on_unpin")).format(time=data["unpin_at_display"])
        else:
            pin_text = await user.get_message("post_pin_on")
    else:
        pin_text = await user.get_message("post_pin_off")

    if data.get("delete_at_display"):
        delete_text = (await user.get_message("post_delete_on")).format(time=data["delete_at_display"])
    else:
        delete_text = await user.get_message("post_delete_off")

    buttons_text = await user.get_message("post_buttons_on") if data.get("buttons") else await user.get_message("post_buttons_off")

    builder.button(text=pin_text, callback_data="POST_SETTINGS_PIN")
    builder.button(text=delete_text, callback_data="POST_SETTINGS_DELETE")
    builder.button(text=buttons_text, callback_data="POST_SETTINGS_BUTTONS")
    builder.button(text=await user.get_message("post_next"), callback_data="POST_NEXT")
    builder.adjust(1)
    return builder.as_markup()


@router.message(Command("start"))
async def h_start(message: types.Message):
    user = models.User(message.chat.id)
    builder = InlineKeyboardBuilder()

    if not await user.get("LANGUAGE"):
        builder.button(text="Ru", callback_data="LANG ru")
        builder.button(text="En", callback_data="LANG en")
        builder.button(text="Es", callback_data="LANG es")

        await message.answer(
            await user.get_message("first_start"), reply_markup=builder.as_markup()
        )
    else:
        keyboard = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [types.KeyboardButton(text=await user.get_message("channels"))],
                [types.KeyboardButton(text=await user.get_message("profile"))],
            ],
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

    if not await channels.get():
        builder.button(text=await user.get_message("add_channel"), callback_data="ADD_CHANNEL")
        builder.adjust(1)
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

    builder.button(text=await user.get_message("add_channel"), callback_data="ADD_CHANNEL")
    builder.adjust(1)

    await message.answer(
        await user.get_message("your_channels"),
        reply_markup=builder.as_markup(),
    )


@router.message(Form.state_entering_channel_data)
async def h_entering_channel_data(message: types.Message, state: FSMContext):
    user = models.User(message.chat.id)
    if message.forward_from:
        print("Короче это пересланное соо")
    elif message.text.lstrip('-').isnumeric():
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
    await state.clear()
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
    builder.button(text=await user.get_message("new_post"), callback_data=f"NEW_POST {channel_id}")
    builder.adjust(1)

    await data.message.answer(await user.get_message("enter_what_you_want_to_change_in_your_channel"), reply_markup=builder.as_markup())


@router.callback_query(CallbackCommandFilter("NEW_POST"))
async def h_new_post(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    channel_id = data.data.split()[1]

    await state.set_data({"channel_id": channel_id})
    await state.set_state(Form.state_waiting_for_post)
    await data.message.answer(await user.get_message("send_me_the_post"))


@router.message(Form.state_waiting_for_post)
async def h_waiting_for_post(message: types.Message, state: FSMContext):
    user = models.User(message.chat.id)

    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        pin=False,
        unpin_at=None,
        unpin_at_display=None,
        delete_at=None,
        delete_at_display=None,
        buttons=None,
    )

    state_data = await state.get_data()
    markup = await _post_settings_markup(user, state_data)
    sent = await message.answer(await user.get_message("post_settings_menu"), reply_markup=markup)
    await state.update_data(settings_message_id=sent.message_id)
    await state.set_state(Form.state_post_settings)


@router.callback_query(Form.state_post_settings, CallbackCommandFilter("POST_SETTINGS_PIN"))
async def h_post_settings_pin(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    state_data = await state.get_data()

    if state_data.get("pin"):
        await state.update_data(pin=False, unpin_at=None, unpin_at_display=None)
        updated = await state.get_data()
        await data.message.edit_reply_markup(reply_markup=await _post_settings_markup(user, updated))
        return

    await state.update_data(pin=True)
    await state.set_state(Form.state_entering_unpin_time)

    builder = InlineKeyboardBuilder()
    builder.button(text=await user.get_message("pin_no_unpin"), callback_data="PIN_NO_UNPIN")
    await data.message.answer(await user.get_message("enter_unpin_time"), reply_markup=builder.as_markup())


@router.callback_query(Form.state_entering_unpin_time, CallbackCommandFilter("PIN_NO_UNPIN"))
async def h_pin_no_unpin(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    await state.update_data(unpin_at=None, unpin_at_display=None)
    await state.set_state(Form.state_post_settings)
    state_data = await state.get_data()
    await data.bot.edit_message_reply_markup(
        chat_id=data.from_user.id,
        message_id=state_data["settings_message_id"],
        reply_markup=await _post_settings_markup(user, state_data),
    )


@router.message(Form.state_entering_unpin_time)
async def h_entering_unpin_time(message: types.Message, state: FSMContext):
    user = models.User(message.chat.id)

    if not message.text:
        await message.answer(await user.get_message("invalid_datetime"))
        return

    tz_offset = float(await user.get("TIMEZONE") or 0)
    dt = time_utils.parse_datetime(message.text, tz_offset)

    if not dt:
        await message.answer(await user.get_message("invalid_datetime"))
        return

    await state.update_data(unpin_at=dt.isoformat(), unpin_at_display=message.text.strip())
    await state.set_state(Form.state_post_settings)
    state_data = await state.get_data()
    await message.answer(await user.get_message("unpin_time_set"))
    try:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=state_data["settings_message_id"],
            reply_markup=await _post_settings_markup(user, state_data),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(Form.state_post_settings, CallbackCommandFilter("POST_SETTINGS_DELETE"))
async def h_post_settings_delete(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    state_data = await state.get_data()

    if state_data.get("delete_at"):
        await state.update_data(delete_at=None, delete_at_display=None)
        updated = await state.get_data()
        await data.message.edit_reply_markup(reply_markup=await _post_settings_markup(user, updated))
        return

    await state.set_state(Form.state_entering_delete_time)
    await data.message.answer(await user.get_message("enter_delete_time"))


@router.message(Form.state_entering_delete_time)
async def h_entering_delete_time(message: types.Message, state: FSMContext):
    user = models.User(message.chat.id)

    if not message.text:
        await message.answer(await user.get_message("invalid_datetime"))
        return

    tz_offset = float(await user.get("TIMEZONE") or 0)
    dt = time_utils.parse_datetime(message.text, tz_offset)

    if not dt:
        await message.answer(await user.get_message("invalid_datetime"))
        return

    await state.update_data(delete_at=dt.isoformat(), delete_at_display=message.text.strip())
    await state.set_state(Form.state_post_settings)
    state_data = await state.get_data()
    await message.answer(await user.get_message("delete_time_set"))
    try:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=state_data["settings_message_id"],
            reply_markup=await _post_settings_markup(user, state_data),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(Form.state_post_settings, CallbackCommandFilter("POST_SETTINGS_BUTTONS"))
async def h_post_settings_buttons(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    state_data = await state.get_data()

    if state_data.get("buttons"):
        await state.update_data(buttons=None)
        updated = await state.get_data()
        await data.message.edit_reply_markup(reply_markup=await _post_settings_markup(user, updated))
        return

    await state.set_state(Form.state_entering_buttons)
    await data.message.answer(await user.get_message("enter_buttons"))


@router.message(Form.state_entering_buttons)
async def h_entering_buttons(message: types.Message, state: FSMContext):
    user = models.User(message.chat.id)

    if not message.text:
        await message.answer(await user.get_message("enter_buttons"))
        return

    await state.update_data(buttons=message.text)
    await state.set_state(Form.state_post_settings)
    state_data = await state.get_data()
    await message.answer(await user.get_message("buttons_set"))
    try:
        await message.bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=state_data["settings_message_id"],
            reply_markup=await _post_settings_markup(user, state_data),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(Form.state_post_settings, CallbackCommandFilter("POST_NEXT"))
async def h_post_next(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    channel_id = (await state.get_data())["channel_id"]

    builder = InlineKeyboardBuilder()
    builder.button(text=await user.get_message("send_now"), callback_data=f"POST_NOW {channel_id}")
    builder.button(text=await user.get_message("add_to_schedule"), callback_data=f"POST_TO_SCHEDULE {channel_id}")
    builder.adjust(1)

    await state.set_state(Form.state_choosing_publish)
    await data.message.answer(await user.get_message("post_publish_menu"), reply_markup=builder.as_markup())


@router.callback_query(Form.state_choosing_publish, CallbackCommandFilter("POST_NOW"))
async def h_post_now(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    state_data = await state.get_data()
    channel_id = data.data.split()[1]

    await aiogram_utils.send_post(
        data.bot, channel_id,
        state_data["from_chat_id"], state_data["message_id"],
        state_data.get("pin", False),
        state_data.get("unpin_at"),
        state_data.get("delete_at"),
        state_data.get("buttons"),
    )
    await data.message.answer(await user.get_message("post_sent"))
    await state.clear()


@router.callback_query(Form.state_choosing_publish, CallbackCommandFilter("POST_TO_SCHEDULE"))
async def h_post_to_schedule(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    state_data = await state.get_data()
    channel_id = data.data.split()[1]

    queue = models.PostsQueue(channel_id)
    await queue.add(
        state_data["from_chat_id"], state_data["message_id"],
        state_data.get("pin", False),
        state_data.get("unpin_at"),
        state_data.get("delete_at"),
        state_data.get("buttons"),
    )
    await data.message.answer(await user.get_message("post_added_to_queue"))
    await state.clear()


@router.callback_query(CallbackCommandFilter("POSTS_SETTINGS"))
async def h_posts_settings(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    channel_id = data.data.split()[1]

    builder = InlineKeyboardBuilder()
    builder.button(text=await user.get_message("set_schedule"), callback_data=f"SCHEDULE_SETTINGS {channel_id}")

    await data.message.answer(await user.get_message("posts_settings_menu"), reply_markup=builder.as_markup())


@router.callback_query(CallbackCommandFilter("SCHEDULE_SETTINGS"))
async def h_schedule_settings(data: types.CallbackQuery, state: FSMContext):
    user = models.User(data.from_user.id)
    channel_id = data.data.split()[1]

    await data.message.answer(await user.get_message("enter_schedule_data"), parse_mode="HTML")
    await state.set_data({"channel_id": channel_id})
    await state.set_state(Form.state_entering_schedule_data)


@router.message(KeyboardCommandFilter("profile"))
async def h_profile(message: types.Message):
    user = models.User(message.chat.id)

    tz_offset = await user.get("TIMEZONE") or 0
    tz_label = f"UTC+{tz_offset}" if float(tz_offset) >= 0 else f"UTC{tz_offset}"

    builder = InlineKeyboardBuilder()
    builder.button(text=await user.get_message("change_timezone"), callback_data="CHANGE_TIMEZONE")
    builder.button(text=await user.get_message("change_language"), callback_data="CHANGE_LANGUAGE")
    builder.adjust(1)

    await message.answer(
        (await user.get_message("profile_info")).format(id=message.chat.id, timezone=tz_label),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(CallbackCommandFilter("CHANGE_TIMEZONE"))
async def h_change_timezone(data: types.CallbackQuery):
    user = models.User(data.from_user.id)

    from datetime import timezone as tz, timedelta
    utc_now = datetime.now(tz.utc)

    builder = InlineKeyboardBuilder()
    offset = -12.0
    while offset < 12.0:
        local_time = utc_now + timedelta(hours=offset)
        builder.button(text=local_time.strftime("%H:%M"), callback_data=f"TZ_SELECT {offset}")
        offset += 0.5
    builder.adjust(6)

    await data.message.answer(await user.get_message("what_time_is_it_now"), reply_markup=builder.as_markup())


@router.callback_query(CallbackCommandFilter("CHANGE_LANGUAGE"))
async def h_change_language(data: types.CallbackQuery):
    user = models.User(data.from_user.id)

    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data="LANG ru")
    builder.button(text="🇬🇧 English", callback_data="LANG en")
    builder.button(text="🇪🇸 Español", callback_data="LANG es")
    builder.adjust(1)

    await data.message.answer(await user.get_message("first_start"), reply_markup=builder.as_markup())


@router.callback_query(CallbackCommandFilter("TZ_SELECT"))
async def h_tz_selected(data: types.CallbackQuery):
    user = models.User(data.from_user.id)

    offset = float(data.data.split()[1])
    await user.set_value("TIMEZONE", offset)

    tz_label = f"UTC+{offset}" if offset >= 0 else f"UTC{offset}"
    await data.message.answer((await user.get_message("timezone_saved")).format(timezone=tz_label))
