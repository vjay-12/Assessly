"""Test all configs and settings without starting services."""
import os
import sys

sys.path.insert(0, "services")
sys.path.insert(0, "services/auth-service")
sys.path.insert(0, "services/api-gateway")

from dotenv import load_dotenv
load_dotenv(".env", override=True)

print("=" * 60)
print("CONFIGURATION TEST")
print("=" * 60)

print("\n[1] Auth Service Config:")
from config import settings as auth_settings
fields = auth_settings.model_dump()
print(f"  DATABASE_URL: {'SET' if fields.get('database_url') != 'postgresql+asyncpg://user:pass@localhost/assessly' else 'DEFAULT'}")
print(f"  REDIS_URL: {'SET' if fields.get('redis_url') != 'redis://valkey:6379' else 'DEFAULT'}")
print(f"  JWT_SECRET: {'SET' if len(fields.get('jwt_secret', '')) > 20 else 'TOO SHORT'}")
print(f"  CROSS_APP_SECRET: {'SET' if len(fields.get('cross_app_secret', '')) > 20 else 'TOO SHORT'}")

print("\n[2] API Gateway Config:")
import importlib.util
spec = importlib.util.spec_from_file_location("gateway_config", "services/api-gateway/config.py")
gateway_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway_module)
gfields = gateway_module.settings.model_dump()
print(f"  DATABASE_URL: {'SET' if gfields.get('database_url') != 'postgresql+asyncpg://user:pass@localhost/assessly' else 'DEFAULT'}")
print(f"  REDIS_URL: {'SET' if gfields.get('redis_url') != 'redis://valkey:6379' else 'DEFAULT'}")
print(f"  JWT_SECRET: {'SET' if len(gfields.get('jwt_secret', '')) > 20 else 'TOO SHORT'}")

print("\n[3] Database Connection Test:")
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_db():
    try:
        engine = create_async_engine(fields['database_url'], echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("  OK - Neon PostgreSQL connected")
            else:
                print("  FAIL - Unexpected response")
        await engine.dispose()
    except Exception as e:
        print(f"  FAIL - {e}")

asyncio.run(test_db())

print("\n[4] Redis Connection Test:")
import redis.asyncio as redis

async def test_redis():
    try:
        client = redis.from_url(fields['redis_url'], decode_responses=True)
        pong = await client.ping()
        if pong:
            print("  OK - Upstash Redis connected")
        await client.close()
    except Exception as e:
        print(f"  FAIL - {e}")

asyncio.run(test_redis())

print("\n[5] Seed Data Check:")
from sqlalchemy import select
from shared.database import AsyncSessionLocal
from shared.models import User, MCQQuestion, Application

async def test_seed():
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(User))
            users = result.scalars().all()
            candidates = len([u for u in users if u.role.value == 'candidate'])
            employers = len([u for u in users if u.role.value == 'employer'])
            print(f"  Users: {len(users)} ({candidates} candidates, {employers} employers)")
            
            result = await session.execute(select(MCQQuestion))
            questions = result.scalars().all()
            print(f"  MCQ Questions: {len(questions)}")
            
            result = await session.execute(select(Application))
            apps = result.scalars().all()
            print(f"  Applications: {len(apps)}")
            
            print("  OK - Seed data verified")
        except Exception as e:
            print(f"  FAIL - {e}")

asyncio.run(test_seed())

print("\n[6] JWT Test:")
from jose import jwt
from datetime import datetime, timedelta

secret = fields['jwt_secret']
algo = fields['jwt_algorithm']
payload = {"sub": "test-user", "role": "candidate", "exp": datetime.utcnow() + timedelta(minutes=30)}
token = jwt.encode(payload, secret, algorithm=algo)
decoded = jwt.decode(token, secret, algorithms=[algo])
print(f"  OK - JWT encode/decode (sub={decoded['sub']}, role={decoded['role']})")

print("\n" + "=" * 60)
print("CONFIG TEST COMPLETE")
print("=" * 60)
