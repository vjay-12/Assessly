import sys
import os

# Add services to path so 'shared' is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services'))

# Set env vars
os.environ['DATABASE_URL'] = "postgresql+asyncpg://neondb_owner:npg_Lcn0zo2Raypq@ep-quiet-king-ao570j8q-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?ssl=require"
os.environ['REDIS_URL'] = "rediss://default:gQAAAAAAAZoNAAIgcDJjMzRjOTE1MDlmNjQ0YzM4OGE0NzcxMzcyYzQ0MWQyMw@rare-barnacle-104973.upstash.io:6379"
os.environ['JWT_SECRET'] = "arUd6_gOuAhk6v6suUvzgAaWMTKdLwYeiCWtN_tgSuI"
os.environ['CROSS_APP_SECRET'] = "hVKrICWOLRBtdIUu3eBLwLGJUx_QM8fcu4qL_oXLnw0"
os.environ['JWT_ALGORITHM'] = "HS256"

# Change to auth-service dir for 'config' import
os.chdir(os.path.join(os.path.dirname(__file__), 'services', 'auth-service'))
sys.path.insert(0, os.getcwd())

try:
    import main
    print("auth-service main.py imported successfully")
except Exception as e:
    print(f"auth-service import failed: {e}")
    import traceback
    traceback.print_exc()
