from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    def __post_init__(self) -> None:
        if not self.BOT_TOKEN:
            raise RuntimeError(
                "BOT_TOKEN environment variable is not set. "
                "Create a .env file based on .env.example or set the variable "
                "before running the bot."
            )

settings = Settings()
