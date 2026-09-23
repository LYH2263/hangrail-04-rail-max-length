from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app as fastapi_app
from app.models.models import HangRail, RailPlacement, Store, WorkOrder


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session, monkeypatch):
    # lifespan 会用 app.main 中绑定的 engine/SessionLocal 建表与播种，替换为内存 SQLite
    import app.database as db_mod
    import app.main as main_mod

    monkeypatch.setattr(db_mod, "engine", db_session.bind)
    monkeypatch.setattr(main_mod, "engine", db_session.bind)
    monkeypatch.setattr(main_mod, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(main_mod.settings, "seed_on_empty", False)

    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


def _make_store_with_rails(db, *, a_limit=80.0, b_limit=None, b_length=160.0):
    store = Store(name="测试店")
    db.add(store)
    db.flush()
    a = HangRail(store_id=store.id, label="A 杆", length_cm=200, max_garment_length_cm=a_limit)
    b = HangRail(store_id=store.id, label="B 杆", length_cm=b_length, max_garment_length_cm=b_limit)
    db.add_all([a, b])
    db.flush()
    return store, a, b


def _make_order(db, store, length_cm, status="ready"):
    order = WorkOrder(
        store_id=store.id,
        ticket_code=f"T-{int(length_cm)}",
        garment_name="羽绒服",
        length_cm=length_cm,
        status=status,
        due_at=datetime.utcnow() + timedelta(days=1),
    )
    db.add(order)
    db.flush()
    return order


def test_long_coat_skips_a_and_hangs_on_b(client, db_session):
    store, a, b = _make_store_with_rails(db_session)
    order = _make_order(db_session, store, 90)
    db_session.commit()

    res = client.post("/api/hang", json={"order_id": order.id})
    assert res.status_code == 200

    placed = db_session.scalars(
        select(RailPlacement).where(RailPlacement.order_id == order.id, RailPlacement.active == 1)
    ).one()
    assert placed.rail_id == b.id  # A 杆上限 80 被跳过，继续试 B


def test_all_rails_over_limit_error_distinguishes_from_no_space(client, db_session):
    store, a, b = _make_store_with_rails(db_session, b_limit=85.0)
    order = _make_order(db_session, store, 90)
    db_session.commit()

    res = client.post("/api/hang", json={"order_id": order.id})
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert "上限" in detail
    assert "空间不足" not in detail


def test_plain_no_space_keeps_original_message(client, db_session):
    # 两根杆都无上限，但都没有空隙 -> 单纯空间不足
    store, a, b = _make_store_with_rails(db_session, a_limit=None)
    db_session.add_all(
        [
            RailPlacement(rail_id=a.id, order_id=_make_order(db_session, store, 200).id, start_cm=0, end_cm=200),
            RailPlacement(rail_id=b.id, order_id=_make_order(db_session, store, 160, status="hung").id, start_cm=0, end_cm=160),
        ]
    )
    target = _make_order(db_session, store, 90)
    db_session.commit()

    res = client.post("/api/hang", json={"order_id": target.id})
    assert res.status_code == 409
    assert res.json()["detail"] == "挂杆空间不足"


def test_unlimited_rail_allows_long_coat(client, db_session):
    store, a, b = _make_store_with_rails(db_session)
    order = _make_order(db_session, store, 90)
    db_session.commit()

    res = client.post("/api/hang", json={"order_id": order.id, "rail_id": b.id})
    assert res.status_code == 200


def test_update_rail_limit_persists(client, db_session):
    store, a, b = _make_store_with_rails(db_session)
    db_session.commit()

    res = client.patch(f"/api/rails/{b.id}", json={"max_garment_length_cm": 100})
    assert res.status_code == 200
    assert res.json()["max_garment_length_cm"] == 100

    res = client.get("/api/rails")
    by_id = {r["id"]: r for r in res.json()}
    assert by_id[a.id]["max_garment_length_cm"] == 80
    assert by_id[b.id]["max_garment_length_cm"] == 100

    # 清空上限
    res = client.patch(f"/api/rails/{b.id}", json={"max_garment_length_cm": None})
    assert res.status_code == 200
    assert res.json()["max_garment_length_cm"] is None
