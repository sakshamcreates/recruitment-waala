import os
from uuid import uuid4

import pytest
from recruitment_api import schema
from recruitment_api.database import get_session
from recruitment_api.ingestion import runner
from recruitment_api.main import app
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def ingestion_db(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL database.")
    namespace = f"ingest_{uuid4().hex}"
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {namespace}"))
    database = create_engine(url, connect_args={"options": f"-csearch_path={namespace}"})
    schema.metadata.create_all(database)
    monkeypatch.setattr(runner, "engine", lambda: database)

    def session():
        with Session(database) as db:
            yield db

    app.dependency_overrides[get_session] = session
    try:
        yield database
    finally:
        app.dependency_overrides.pop(get_session, None)
        database.dispose()
        with admin.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {namespace} CASCADE"))
        admin.dispose()
