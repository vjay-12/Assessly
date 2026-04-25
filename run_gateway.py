import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services'))

os.environ['DATABASE_URL'] = "postgresql+asyncpg://neondb_owner:npg_Lcn0zo2Raypq@ep-quiet-king-ao570j8q-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?ssl=require"
os.environ['REDIS_URL'] = "rediss://default:gQAAAAAAAZoNAAIgcDJjMzRjOTE1MDlmNjQ0YzM4OGE0NzcxMzcyYzQ0MWQyMw@rare-barnacle-104973.upstash.io:6379"
os.environ['JWT_SECRET'] = "arUd6_gOuAhk6v6suUvzgAaWMTKdLwYeiCWtN_tgSuI"
os.environ['JWT_ALGORITHM'] = "HS256"
os.environ['AUTH_SERVICE_URL'] = "http://localhost:3001"

os.chdir(os.path.join(os.path.dirname(__file__), 'services', 'api-gateway'))
sys.path.insert(0, os.getcwd())

import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=False)
