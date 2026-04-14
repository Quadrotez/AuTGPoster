import os

from aiogram import types

import json
from dotenv import load_dotenv

from database import db
from utils import languages

load_dotenv()

class User:
    def __init__(self, chat_id: int):
        self.chat_id = chat_id

    async def exists(self):
        return bool(
            await db.execute(
                "SELECT * FROM USERS WHERE CHAT_ID = ?", (self.chat_id,), fetch=True
            )
        )

    async def init(self, message: types.Message):
        await db.execute(
            """
        INSERT INTO USERS (CHAT_ID) VALUES
        (?)
        """,
            (self.chat_id,),
        )

    async def get_message(self, message: str) -> str:
        if not await self.exists() or not await self.get("LANGUAGE"):
            self.language = os.environ["DEFAULT_LANGUAGE"]
        else:
            self.language = str(await db.execute("SELECT LANGUAGE FROM USERS WHERE CHAT_ID = ?",
                                    (self.chat_id,), fetch=True))
        return languages.get_message(self.language, message)
    
    async def set_value(self, key: str, value: any):
        await db.execute(f"UPDATE USERS SET {key}=? WHERE CHAT_ID = ?",
        (value, self.chat_id))
        

    async def get(self, key: str):
        return await db.execute(f"SELECT {key} FROM USERS WHERE CHAT_ID = ?", (self.chat_id,), fetch=True)


class Channels:
    def __init__(self, chat_id: str | int | None = None):
        self.chat_id = chat_id

    async def get(self):
        channels = await db.execute("SELECT CHAT_ID FROM CHANNELS", fetch=True, force_list=True)
        
        admin_channels = []

        for iter_channel in channels:
            channel = Channel(iter_channel)

            admins_id = json.loads(await channel.get("ADMINS_IDES"))

            admin_channels.append(await channel.get("CHAT_ID")) if self.chat_id in admins_id else None
            
            
        return admin_channels

class Channel:
    def __init__(self, channel_id: str | int) -> None:
        self.chat_id = channel_id

    async def init(self, admins_id, owner_id, channel_name):
        await db.execute("INSERT INTO CHANNELS (CHAT_ID, ADMINS_IDES, OWNER_ID, CHANNEL_NAME) VALUES (?, ?, ?, ?)", 
        (self.chat_id, json.dumps(list(admins_id)), owner_id, channel_name))

    async def set_value(self, key: str, value: any):
        await db.execute(f"UPDATE CHANNELS SET {key}=? WHERE CHAT_ID = ?",
        (value, self.chat_id))

    async def get(self, key: str):
        return await db.execute(f"SELECT {key} FROM CHANNELS WHERE CHAT_ID = ?", (self.chat_id,), fetch=True)


class PostsQueue:
    def __init__(self, channel_id: str | int) -> None:
        self.channel_id = channel_id

    async def add(self, from_chat_id: int, message_id: int, pin: bool = False,
                  unpin_at: str | None = None, delete_at: str | None = None,
                  buttons: str | None = None):
        await db.execute(
            "INSERT INTO POSTS_QUEUE (CHANNEL_ID, FROM_CHAT_ID, MESSAGE_ID, PIN, UNPIN_AT, DELETE_AT, BUTTONS) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.channel_id, from_chat_id, message_id, int(pin), unpin_at, delete_at, buttons)
        )

    async def get_next(self):
        return await db.execute(
            "SELECT ID, FROM_CHAT_ID, MESSAGE_ID, PIN, UNPIN_AT, DELETE_AT, BUTTONS FROM POSTS_QUEUE WHERE CHANNEL_ID = ? ORDER BY ID LIMIT 1",
            (self.channel_id,), fetch=True
        )

    async def remove(self, post_id: int):
        await db.execute("DELETE FROM POSTS_QUEUE WHERE ID = ?", (post_id,))


class SentPost:
    @staticmethod
    async def add(channel_id: int, message_id: int, unpin_at: str | None, delete_at: str | None):
        await db.execute(
            "INSERT INTO SENT_POSTS (CHANNEL_ID, MESSAGE_ID, UNPIN_AT, DELETE_AT) VALUES (?, ?, ?, ?)",
            (channel_id, message_id, unpin_at, delete_at)
        )
        