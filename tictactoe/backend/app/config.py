import os

from attr import dataclass

@dataclass(frozen=True)
class Settings:
    database_url: tuple[str, ...] = os.getenv("DATABASE_URL", "./tictactoe.db"), # add an os.getenv("DATABASE_URL", "./tictactoe.db") to get the database url from environment variable
    engine_version: tuple[str] = os.getenv("ENGINE_VERSION", "1"),
    log_level: tuple[str] = os.getenv("LOG_LEVEL", "INFO"),
    allowed_origins: list[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")

    def load_settings(self):
        self.database_url = os.getenv("DATABASE_URL", self.database_url)
        self.engine_version = os.getenv("ENGINE_VERSION", self.engine_version)
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", self.allowed_origins).split(",")