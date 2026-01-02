from aiogram import types

from database import db


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