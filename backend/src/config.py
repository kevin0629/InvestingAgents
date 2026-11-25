from pydantic import PostgresDsn
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    DATABASE_URL: PostgresDsn = "postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}".format(
                        user = "postgres",
                        password = "113423027",
                        host = "127.0.0.1",
                        port = "5432",
                        database = "stock"
                    )
    
    CORS_ORIGINS: list[str] = ["http://localhost", "http://127.0.0.1", "http://localhost:4200", "http://127.0.0.1:4200"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]

    APP_VERSION: str = "1.0.0"