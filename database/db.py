import aiosqlite
import os

from dotenv import load_dotenv

load_dotenv()

database_path = os.environ["DATABASE_PATH"]


async def init_database():
    async with aiosqlite.connect(database_path) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS USERS (
            CHAT_ID INT PRIMARY KEY, 
            ROLE TEXT DEFAULT USER,
            LANGUAGE TEXT
            )""")
        
        await db.execute("""CREATE TABLE IF NOT EXISTS CHANNELS (
        CHAT_ID INT PRIMARY KEY, 
        ADMINS_IDES JSON DEFAULT [],
        OWNER_ID INT,
        CHANNEL_NAME TEXT
        )""")
        await db.close()


async def execute(query: str, params: list | tuple | set = [], fetch=False, force_list=False):
    result_fetch = []

    db = aiosqlite.connect(database_path)

    async with db:
        r = await db.execute(query, params)

        await db.commit()

        if fetch:
            r = list(await r.fetchall())

            if not r:
                result_fetch = []

            if len(r) == 1:
                result_fetch = r[0]

                if len(r[0]) == 1:
                    result_fetch = r[0][0]

            elif len(r) > 1:
                result_fetch = [i[0] for i in r]
            
            if force_list:
                result_fetch = result_fetch if type(result_fetch) is list else [result_fetch]

        await db.close()

        return result_fetch
