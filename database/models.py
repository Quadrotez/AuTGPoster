import os

from aiogram import types

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
        if not await self.exists():
            self.language = os.environ["DEFAULT_LANGUAGE"]
        else:
            self.language = str(await db.execute("SELECT LANGUAGE FROM USERS WHERE CHAT_ID = ?",
                                    (self.chat_id,), fetch=True))
        return languages.get_message(self.language, message)
    
    async def set_value(self, key: str, value: any):
        await db.execute(f"UPDATE USERS SET {key}=? WHERE CHAT_ID = ?",
        (value, self.chat_id))
        
