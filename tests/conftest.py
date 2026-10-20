
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app

from app.core.security import create_access_token
from app.models.models import User, UserStatus, Role


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL must be set to the paw_pantry_test database."
    )

if not TEST_DATABASE_URL.endswith("/paw_pantry_test"):
    raise RuntimeError(
        "Tests must use the dedicated paw_pantry_test database."
    )

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def prepare_test_database():
    import app.models  # noqa: F401

    if test_engine.connect().exec_driver_sql(
        "SELECT current_database()"
    ).scalar_one() != "paw_pantry_test":
        raise RuntimeError("Connected to the wrong test database.")

    Base.metadata.create_all(bind=test_engine)
    yield
    # Intentionally do not drop tables automatically.
    test_engine.dispose()


@pytest.fixture()
def db_session(prepare_test_database):
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
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()

@pytest.fixture
def user_headers(db_session):
    user = User(
        id=uuid.uuid4(),
        email="regular-test@example.com",
        email_normalized="regular-test@example.com",
        display_name="Regular Test User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.flush()

    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(db_session):
    user = User(
        id=uuid.uuid4(),
        email="admin-test@example.com",
        email_normalized="admin-test@example.com",
        display_name="Admin Test User",
        status=UserStatus.ACTIVE,
    )

    role = db_session.query(Role).filter_by(name="admin").first()
    if role is None:
        role = Role(id=1, name="admin")
        db_session.add(role)

    user.roles.append(role)
    db_session.add(user)
    db_session.flush()

    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}
