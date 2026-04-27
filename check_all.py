"""
Comprehensive health check for all Assessly platform components.
"""
import asyncio
import os
import re
import sys
import httpx

# Auto-detect env vars from run_auth.py
with open("run_auth.py", "r") as f:
    content = f.read()
for key in ["DATABASE_URL", "REDIS_URL", "JWT_SECRET", "CROSS_APP_SECRET", "JWT_ALGORITHM"]:
    pattern = r'os\.environ\[[\'"]' + re.escape(key) + r'[\'"]\]\s*=\s*"([^"]+)"'
    match = re.search(pattern, content)
    if match:
        os.environ[key] = match.group(1)

sys.path.insert(0, "services")
from shared.database import init_engine, DB
from shared.models import AuditLog, AuditEventType, AuditEventCategory, SeverityLevel
from sqlalchemy import text


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def ok(msg):
    print(f"  [PASS] {msg}")

def fail(msg):
    print(f"  [FAIL] {msg}")

async def check_auth_service():
    print_header("AUTH SERVICE (localhost:3001)")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://localhost:3001/health")
            if resp.status_code == 200:
                ok(f"Health: {resp.json()}")
            else:
                fail(f"Health returned {resp.status_code}")
            
            resp = await client.post(
                "http://localhost:3001/auth/login",
                json={"email": "test@test.com", "password": "wrong"}
            )
            if resp.status_code in (401, 422):
                ok(f"Login endpoint responsive (status {resp.status_code})")
            else:
                fail(f"Login unexpected status {resp.status_code}")
    except Exception as e:
        fail(f"Auth service unreachable: {e}")

async def check_gateway():
    print_header("API GATEWAY (localhost:3000)")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://localhost:3000/health")
            if resp.status_code == 200:
                ok(f"Health: {resp.json()}")
            else:
                fail(f"Health returned {resp.status_code}")
    except Exception as e:
        fail(f"Gateway unreachable: {e}")

async def check_frontend(name, port):
    print_header(f"{name} (localhost:{port})")
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
            resp = await client.get(f"http://localhost:{port}")
            if resp.status_code == 200:
                text = resp.text
                if "<!DOCTYPE html>" in text or "<html" in text:
                    ok(f"Serving HTML (status {resp.status_code})")
                else:
                    ok(f"Responding (status {resp.status_code}, len={len(text)})")
            elif resp.status_code in (301, 302, 307, 308):
                ok(f"Redirecting (status {resp.status_code})")
            else:
                fail(f"Unexpected status {resp.status_code}")
    except Exception as e:
        fail(f"Frontend unreachable: {e}")

async def check_database():
    print_header("DATABASE (Neon PostgreSQL)")
    try:
        await init_engine(retries=3, base_delay=1)
        ok("Connection established via shared.database")
        
        async with DB.engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        ok("Test query passed")
        
        # Check audit_logs columns
        async with DB.engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'audit_logs'
            """))
            cols = result.fetchall()
        col_names = [c[0] for c in cols]
        if "category" in col_names:
            ok("audit_logs.category column exists")
        else:
            fail("audit_logs.category column MISSING")
        
        if "assessment_id" in col_names:
            ok("audit_logs.assessment_id column exists")
        else:
            fail("audit_logs.assessment_id column MISSING")
        
        # Check key tables
        async with DB.engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
            """))
            tables = result.fetchall()
        table_names = [t[0] for t in tables]
        for expected in ["users", "assessments", "questions", "test_sessions", "audit_logs"]:
            if expected in table_names:
                ok(f"Table '{expected}' exists")
            else:
                fail(f"Table '{expected}' MISSING")
        
        # Check Redis
        redis_url = os.getenv("REDIS_URL", "")
        if redis_url:
            try:
                import redis.asyncio as aioredis
                r = aioredis.from_url(redis_url, socket_connect_timeout=5)
                await r.ping()
                ok("Redis connection OK")
                await r.aclose()
            except Exception as e:
                fail(f"Redis connection failed: {e}")
        
        await DB.engine.dispose()
    except Exception as e:
        fail(f"Database connection failed: {e}")

async def main():
    print("=" * 60)
    print("  ASSESSLY PLATFORM - COMPONENT HEALTH CHECK")
    print("=" * 60)
    
    await check_auth_service()
    await check_gateway()
    await check_frontend("CANDIDATE PORTAL", 4000)
    await check_frontend("ASSESSMENT ENGINE", 4001)
    await check_frontend("EMPLOYER DASHBOARD", 4002)
    await check_database()
    
    print("\n" + "=" * 60)
    print("  CHECK COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
