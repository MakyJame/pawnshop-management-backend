from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

from sqlalchemy.engine import make_url

def validate_test_database() -> None:
    if not settings.test_database_url:
        raise RuntimeError("TEST_DATABASE_URL is not configured.")

    test_url = make_url(settings.test_database_url)
    dev_url = make_url(settings.database_url)

    if test_url.database != "pawn_management_test":
        raise RuntimeError(
            "Unsafe test database: expected pawn_management_test."
        )

    if test_url == dev_url:
        raise RuntimeError(
            "TEST_DATABASE_URL must not equal DATABASE_URL."
        )


validate_test_database()

test_engine = create_engine(
    settings.test_database_url,
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()

    session = TestingSessionLocal(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(
    db_session: Session,
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
