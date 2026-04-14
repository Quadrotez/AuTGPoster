from aiogram import Bot
from aiogram.types import ChatMemberOwner
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db


async def get_channel_owner(bot: Bot, channel_id: str | int):
    admins = await bot.get_chat_administrators(channel_id)

    for admin in admins:
        if isinstance(admin, ChatMemberOwner):
            return admin.user.id

    return None


async def send_post(
    bot: Bot,
    channel_id: int | str,
    from_chat_id: int,
    message_id: int,
    pin: bool = False,
    unpin_at: str | None = None,
    delete_at: str | None = None,
    buttons: str | None = None,
):
    buttons_markup = None
    if buttons:
        b = InlineKeyboardBuilder()
        for line in buttons.strip().split("\n"):
            if " - " in line:
                title, url = line.split(" - ", 1)
                b.button(text=title.strip(), url=url.strip())
        b.adjust(1)
        buttons_markup = b.as_markup()

    result = await bot.copy_message(
        chat_id=channel_id,
        from_chat_id=from_chat_id,
        message_id=message_id,
        reply_markup=buttons_markup,
    )

    if pin:
        await bot.pin_chat_message(chat_id=channel_id, message_id=result.message_id, disable_notification=True)

    if unpin_at or delete_at:
        await db.execute(
            "INSERT INTO SENT_POSTS (CHANNEL_ID, MESSAGE_ID, UNPIN_AT, DELETE_AT) VALUES (?, ?, ?, ?)",
            (channel_id, result.message_id, unpin_at, delete_at)
        )
