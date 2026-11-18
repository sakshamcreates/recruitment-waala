import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


def database_url() -> URL:
    load_dotenv(".env")
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("Set DATABASE_URL before running database commands.")
    try:
        url = make_url(value)
    except (ArgumentError, ValueError):
        raise RuntimeError("DATABASE_URL is not a valid PostgreSQL connection URL.") from None
    if url.drivername != "postgresql+psycopg" or not url.database:
        raise RuntimeError("DATABASE_URL must use postgresql+psycopg and name a database.")
    return url
