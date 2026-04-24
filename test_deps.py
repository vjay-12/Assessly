deps = [
    "fastapi", "sqlalchemy", "asyncpg", "redis", "jose", "passlib", "bcrypt",
    "pydantic", "pydantic_settings", "uvicorn", "prometheus_fastapi_instrumentator",
    "arq"
]
for dep in deps:
    try:
        __import__(dep)
        print(f"OK: {dep}")
    except ImportError as e:
        print(f"MISSING: {dep} - {e}")
