import aiosqlite
import os

database_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "db.db")


async def init_database():
    os.makedirs(os.path.dirname(database_path), exist_ok=True)
    async with aiosqlite.connect(database_path) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS USERS (
            CHAT_ID INT PRIMARY KEY, 
            ROLE TEXT DEFAULT USER,
            LANGUAGE TEXT,
            TIMEZONE INT DEFAULT 0
            )""")

        try:
            await db.execute("ALTER TABLE USERS ADD COLUMN TIMEZONE INT DEFAULT 0")
        except Exception:
            pass
        
        await db.execute("""CREATE TABLE IF NOT EXISTS CHANNELS (
        CHAT_ID INT PRIMARY KEY, 
        ADMINS_IDES JSON DEFAULT '[]',
        OWNER_ID INT,
        CHANNEL_NAME TEXT,
        SCHEDULE_DATA JSON DEFAULT '{}'
        )""")

        await db.execute("""CREATE TABLE IF NOT EXISTS POSTS_QUEUE (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        CHANNEL_ID INT,
        FROM_CHAT_ID INT,
        MESSAGE_ID INT,
        PIN INT DEFAULT 0,
        UNPIN_AT TEXT,
        DELETE_AT TEXT,
        BUTTONS TEXT,
        SCHEDULED_AT TEXT
        )""")

        for col in ["PIN INT DEFAULT 0", "UNPIN_AT TEXT", "DELETE_AT TEXT", "BUTTONS TEXT", "SCHEDULED_AT TEXT"]:
            try:
                await db.execute(f"ALTER TABLE POSTS_QUEUE ADD COLUMN {col}")
            except Exception:
                pass

        await db.execute("""CREATE TABLE IF NOT EXISTS SENT_POSTS (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        CHANNEL_ID INT,
        MESSAGE_ID INT,
        UNPIN_AT TEXT,
        DELETE_AT TEXT
        )""")

        await db.commit()
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
