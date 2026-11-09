from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    allowed_origins: list[str] = ["http://localhost:3000"]
    history_size: int = 20
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
