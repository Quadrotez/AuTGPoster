from aiogram import Bot
from aiogram.types import ChatMemberOwner

async def get_channel_owner(bot: Bot, channel_id: str | int):
    admins = await bot.get_chat_administrators(channel_id)

    for admin in admins:
        if isinstance(admin, ChatMemberOwner):
            return admin.user.id

    return None