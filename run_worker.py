import sys
import os

# Add services directory to path so 'shared' is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services'))
os.environ['PYTHONPATH'] = 'services'

# Set env vars
os.environ['DATABASE_URL'] = "postgresql+asyncpg://neondb_owner:npg_Lcn0zo2Raypq@ep-quiet-king-ao570j8q-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?ssl=require"
os.environ['REDIS_URL'] = "rediss://default:gQAAAAAAAZoNAAIgcDJjMzRjOTE1MDlmNjQ0YzM4OGE0NzcxMzcyYzQ0MWQyMw@rare-barnacle-104973.upstash.io:6379"
os.environ['JWT_SECRET'] = "arUd6_gOuAhk6v6suUvzgAaWMTKdLwYeiCWtN_tgSuI"
os.environ['JWT_ALGORITHM'] = "HS256"
os.environ['WORKER_ID'] = "worker-1"

# Change to evaluation-worker dir
os.chdir(os.path.join(os.path.dirname(__file__), 'services', 'evaluation-worker'))
sys.path.insert(0, os.getcwd())

import asyncio
from main import main

if __name__ == "__main__":
    print("[WORKER] Starting evaluation worker...")
    asyncio.run(main())
