import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/assessly")
    redis_url: str = os.getenv("REDIS_URL", "redis://valkey:6379")
    jwt_secret: str = os.getenv("JWT_SECRET", "supersecretkey")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")


settings = Settings()
