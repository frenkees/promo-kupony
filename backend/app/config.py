from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXPIRE_DAYS: int = 30
    COOKIE_SECURE: bool = True

    MASTER_LOGIN: str
    MASTER_PASSWORD: str

    NIGHT_WINDOW_START: int = 0
    NIGHT_WINDOW_END: int = 6

    QR_PREFIX: str = "PROMO"


settings = Settings()
