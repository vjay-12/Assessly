import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    url = os.getenv("DATABASE_URL")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [row[0] for row in result.fetchall()]
        print("Tables:", tables)
        for t in tables:
            try:
                r = await conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
                print(f"  {t}: {r.scalar()} rows")
            except Exception as e:
                print(f"  {t}: error - {e}")
    await engine.dispose()

asyncio.run(check())
