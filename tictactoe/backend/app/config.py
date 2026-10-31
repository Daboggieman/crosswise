import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_path: str = "./tictactoe.db"
    migrations_dir: str = "./migrations"
    engine_version: str = "1"
    log_level: str = "INFO"
    allowed_origins: tuple[str, ...] = ("*",)
    frontend_dir: str = "../frontend"

    @classmethod
    def load_settings(cls):
        return cls(
            database_path=os.getenv("DATABASE_URL", "./tictactoe.db"),
            migrations_dir=os.getenv("MIGRATIONS_DIR", "./migrations"),
            engine_version=os.getenv("ENGINE_VERSION", "1"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            allowed_origins=tuple(os.getenv("ALLOWED_ORIGINS", "*").split(",")),
            frontend_dir=os.getenv("FRONTEND_DIR", "../frontend")
        )


def get_settings() -> Settings:
    return Settings.load_settings()
