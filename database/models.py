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
    def __init__(self, chat_id: str | int) -> None:
        self.chat_id = chat_id

    async def init(self, admins_id, owner_id, channel_name):
        await db.execute("INSERT INTO CHANNELS (CHAT_ID, ADMINS_IDES, OWNER_ID, CHANNEL_NAME) VALUES (?, ?, ?, ?)", 
        (self.chat_id, json.dumps(list(admins_id)), owner_id, channel_name))


    async def set_value(self, key: str, value: any):
        await db.execute(f"UPDATE CHANNELS SET {key}=? WHERE CHAT_ID = ?",
        (value, self.chat_id))

    async def get(self, key: str):
        return await db.execute(f"SELECT {key} FROM CHANNELS WHERE CHAT_ID = ?", (self.chat_id,), fetch=True)
        