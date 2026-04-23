import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/zetheta")
    redis_url: str = os.getenv("REDIS_URL", "redis://valkey:6379")
    jwt_secret: str = os.getenv("JWT_SECRET", "supersecretkey")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    jwt_refresh_token_expire_days: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    cross_app_secret: str = os.getenv("CROSS_APP_SECRET", "crossappsecret")
    cross_app_token_expire_seconds: int = int(os.getenv("CROSS_APP_TOKEN_EXPIRE_SECONDS", "120"))


settings = Settings()
