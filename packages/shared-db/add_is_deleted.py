import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

os.environ['DATABASE_URL'] = "postgresql+asyncpg://neondb_owner:npg_Lcn0zo2Raypq@ep-quiet-king-ao570j8q-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?ssl=require"

engine = create_async_engine(os.getenv('DATABASE_URL'), echo=False)

async def main():
    async with engine.begin() as conn:
        await conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE'))
        print('Column is_deleted added successfully')
    await engine.dispose()

asyncio.run(main())
