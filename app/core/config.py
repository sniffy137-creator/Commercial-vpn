from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Важно:
    # - case_sensitive=False: DATABASE_URL и database_url нормально мапятся
    # - extra="ignore": чтобы любые лишние переменные (например TEST_DATABASE_URL) не валили приложение
    # - env_file=".env": файл как fallback, но приоритет у переменных окружения
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Commercial VPN API"
    env: str = "dev"

    database_url: str

    jwt_secret: str
    jwt_alg: str = "HS256"
    access_token_expire_min: int = 60


settings = Settings()
