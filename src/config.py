import os

from dotenv import load_dotenv


load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_optional_env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)
