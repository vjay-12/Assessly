"""
Migration script to add missing columns to audit_logs table.
Auto-detects DATABASE_URL from run_auth.py
"""
import asyncio
import os
import asyncpg
import re

# Auto-detect DATABASE_URL from run_auth.py
with open("run_auth.py", "r") as f:
    content = f.read()
match = re.search(r'os\.environ\[.DATABASE_URL.\]\s*=\s*"([^"]+)"', content)
if match:
    os.environ["DATABASE_URL"] = match.group(1)

async def migrate():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not found in run_auth.py")
        return

    # Convert SQLAlchemy asyncpg URL to plain asyncpg DSN
    dsn = url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(dsn)
    try:
        # Check if category column exists
        col = await conn.fetchval("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'audit_logs' AND column_name = 'category'
        """)
        if col:
            print("[OK] category column already exists")
        else:
            await conn.execute("""
                ALTER TABLE audit_logs
                ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'System'
            """)
            print("[OK] Added category column")

        # Check if assessment_id column exists
        col = await conn.fetchval("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'audit_logs' AND column_name = 'assessment_id'
        """)
        if col:
            print("[OK] assessment_id column already exists")
        else:
            await conn.execute("""
                ALTER TABLE audit_logs
                ADD COLUMN assessment_id UUID REFERENCES assessments(id) ON DELETE SET NULL
            """)
            print("[OK] Added assessment_id column")

        # Create indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_audit_category ON audit_logs(category)")
        print("[OK] Created ix_audit_category index")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_audit_assessment ON audit_logs(assessment_id)")
        print("[OK] Created ix_audit_assessment index")

        print("\n[OK] Migration completed successfully!")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
