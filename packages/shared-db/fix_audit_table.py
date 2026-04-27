"""Fix audit_logs table — add missing columns or recreate with new schema."""
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Use the same DB URL as the app
DB_URL = os.getenv("DATABASE_URL", "")
if not DB_URL:
    raise RuntimeError("DATABASE_URL not set")

async def main():
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        # Check if audit_logs exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'audit_logs')"
        ))
        exists = result.scalar()

        if exists:
            # Check if category column exists
            result = await conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'audit_logs' AND column_name = 'category')"
            ))
            has_category = result.scalar()

            if not has_category:
                print("Adding missing columns to audit_logs...")
                await conn.execute(text("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'System'"))
                await conn.execute(text("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS assessment_id UUID REFERENCES assessments(id) ON DELETE SET NULL"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_category ON audit_logs(category)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_assessment ON audit_logs(assessment_id)"))
                print("Migration complete.")
            else:
                print("audit_logs already has all columns.")
        else:
            print("audit_logs table does not exist. It will be created by SQLAlchemy on next app startup.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
