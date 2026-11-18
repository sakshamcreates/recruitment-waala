import os

from dotenv import load_dotenv


def setting(name: str) -> str | None:
    load_dotenv(".env")
    return os.getenv(name)
