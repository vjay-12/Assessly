import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def drop():
    url = os.getenv("DATABASE_URL")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        # Drop all tables
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [row[0] for row in result.fetchall()]
        for t in tables:
            await conn.execute(text(f"DROP TABLE IF EXISTS {t} CASCADE"))
            print(f"Dropped table {t}")

        # Drop all custom enum types
        result = await conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e' AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')"))
        enums = [row[0] for row in result.fetchall()]
        for e in enums:
            await conn.execute(text(f"DROP TYPE IF EXISTS {e} CASCADE"))
            print(f"Dropped enum {e}")
    await engine.dispose()

asyncio.run(drop())
