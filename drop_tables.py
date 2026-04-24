import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def drop():
    url = os.getenv("DATABASE_URL")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [row[0] for row in result.fetchall()]
        for t in tables:
            await conn.execute(text(f"DROP TABLE IF EXISTS {t} CASCADE"))
            print(f"Dropped {t}")
    await engine.dispose()

asyncio.run(drop())
