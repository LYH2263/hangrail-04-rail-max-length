import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import HangRail, WorkOrder
from app.services.seed import seed_if_empty


@pytest.fixture
def env():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    seed_if_empty(db)
    db.close()

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    def order(ticket_code: str, session=None):
        own = session is None
        session = session or TestingSession()
        try:
            return session.scalar(select(WorkOrder).where(WorkOrder.ticket_code == ticket_code))
        finally:
            if own:
                session.close()

    def rail(label: str, session=None):
        own = session is None
        session = session or TestingSession()
        try:
            return session.scalar(select(HangRail).where(HangRail.label == label))
        finally:
            if own:
                session.close()

    # Deliberately not entered as a context manager: that would trigger the
    # lifespan against the configured Postgres engine. Tables above already
    # exist on this in-memory SQLite engine.
    yield {"client": TestClient(app), "session": TestingSession, "order": order, "rail": rail}
    app.dependency_overrides.clear()
    engine.dispose()
