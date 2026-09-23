from sqlalchemy import select

from app.models.models import RailPlacement


def _fill_gaps(session, env):
    """填满 A、B 杆的剩余空隙（A 已占 0-80，B 已占 0-40）。"""
    a = env["rail"]("A 杆")
    b = env["rail"]("B 杆")
    filler = env["order"]("HR-2003").id
    session.add_all(
        [
            RailPlacement(rail_id=a.id, order_id=filler, start_cm=80, end_cm=200, active=1),
            RailPlacement(rail_id=b.id, order_id=filler, start_cm=40, end_cm=160, active=1),
        ]
    )
    session.commit()


def test_long_coat_skips_capped_rail_and_lands_on_b(env):
    # 种子：A 杆上限 80，羽绒服衣长 90。A 空余足够也必须跳过，继续试 B 并成功。
    order_id = env["order"]("HR-2003").id
    res = env["client"].post("/api/hang", json={"order_id": order_id})
    assert res.status_code == 200
    assert res.json()["status"] == "hung"

    session = env["session"]()
    try:
        order = env["order"]("HR-2003", session)
        active = session.scalars(
            select(RailPlacement).where(RailPlacement.order_id == order.id, RailPlacement.active == 1)
        ).all()
        assert len(active) == 1
        assert active[0].rail_id == env["rail"]("B 杆", session).id
        assert active[0].start_cm == 40
        assert active[0].end_cm == 130
    finally:
        session.close()


def test_all_rails_over_cap_returns_distinct_error(env):
    # 全店可试挂杆都因衣长上限拒挂 → 错误区别于单纯无空隙
    session = env["session"]()
    try:
        env["rail"]("B 杆", session).max_garment_cm = 80
        session.commit()
        order_id = env["order"]("HR-2003", session).id
    finally:
        session.close()

    res = env["client"].post("/api/hang", json={"order_id": order_id})
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail != "挂杆空间不足"
    assert "衣长" in detail and "上限" in detail


def test_pure_no_space_returns_space_error(env):
    # 连衣裙衣长 30，未超任何杆上限；两杆填满 → 单纯无空隙错误
    session = env["session"]()
    try:
        _fill_gaps(session, env)
        order_id = env["order"]("HR-2004", session).id
    finally:
        session.close()

    res = env["client"].post("/api/hang", json={"order_id": order_id})
    assert res.status_code == 409
    assert res.json()["detail"] == "挂杆空间不足"


def test_uncapped_rail_accepts_long_garment(env):
    # B 杆未配置上限：即使 A 杆上限 80，指定挂 B 的 90cm 羽绒服可成功
    session = env["session"]()
    try:
        order_id = env["order"]("HR-2003", session).id
        b_id = env["rail"]("B 杆", session).id
        assert env["rail"]("B 杆", session).max_garment_cm is None
    finally:
        session.close()

    res = env["client"].post("/api/hang", json={"order_id": order_id, "rail_id": b_id})
    assert res.status_code == 200
    assert res.json()["status"] == "hung"


def test_patch_rail_cap_persists(env):
    a_id = env["rail"]("A 杆").id

    res = env["client"].patch(f"/api/rails/{a_id}", json={"max_garment_cm": 120})
    assert res.status_code == 200
    assert res.json()["max_garment_cm"] == 120

    # 重新获取（模拟再次进入页面）上限仍在
    res = env["client"].get("/api/rails")
    caps = {r["label"]: r["max_garment_cm"] for r in res.json()}
    assert caps["A 杆"] == 120
    assert caps["B 杆"] is None

    # 清空上限 → 不限衣长
    res = env["client"].patch(f"/api/rails/{a_id}", json={"max_garment_cm": None})
    assert res.status_code == 200
    assert res.json()["max_garment_cm"] is None
