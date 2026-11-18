from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session

from .settings import setting


class DatabaseConfigurationError(RuntimeError):
    pass


def database_url() -> URL:
    value = setting("DATABASE_URL")
    if not value:
        raise DatabaseConfigurationError("Set DATABASE_URL before running database commands.")
    try:
        url = make_url(value)
    except (ArgumentError, ValueError):
        raise DatabaseConfigurationError(
            "DATABASE_URL is not a valid PostgreSQL connection URL."
        ) from None
    if url.drivername != "postgresql+psycopg" or not url.database:
        raise DatabaseConfigurationError(
            "DATABASE_URL must use postgresql+psycopg and name a database."
        )
    return url


@lru_cache
def engine():
    return create_engine(
        database_url(),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 3},
    )


def get_session():
    with Session(engine()) as session:
        yield session
