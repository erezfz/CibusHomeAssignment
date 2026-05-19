from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from domains.models import DBConnectionSettings

ROOT_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    db_name: str = Field(alias="DB_NAME")
    db_port: int = Field(alias="DB_PORT")
    db_host: str = Field(alias="DB_HOST")
    db_username: str = Field(alias="DB_USERNAME")
    db_password: str = Field(alias="DB_PASSWORD")

    jwt_secret: str = Field(alias="JWT_SECRET")

    server_host: str = Field(default="127.0.0.1", alias="SERVER_HOST")
    server_port: int = Field(default=8000, alias="SERVER_PORT")

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",          # local/testing convenience
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    @property
    def db_settings(self) -> DBConnectionSettings:
        return DBConnectionSettings(
            db_name=self.db_name,
            db_port=self.db_port,
            db_url=self.db_host,
            db_username=self.db_username,
            db_password=self.db_password,
        )

@lru_cache
def get_settings() -> Settings:
    """
    Cached singleton settings object.

    Prevents reparsing env variables repeatedly.
    """
    return Settings()





