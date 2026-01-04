from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    app_name: str = "Commercial VPN API"
    env: str = "dev"
    database_url: str

    jwt_secret: str
    jwt_alg: str = "HS256"
    access_token_expire_min: int = 60


settings = Settings()
