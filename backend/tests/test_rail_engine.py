from app.services.rail_engine import Segment, first_fit, free_gaps


def test_first_fit_leftmost():
    occ = [Segment(20, 40)]
    p = first_fit(100, occ, 15)
    assert p is not None
    assert p.start_cm == 0
    assert p.end_cm == 15


def test_first_fit_skips_too_small_gap():
    occ = [Segment(0, 10), Segment(18, 50)]
    p = first_fit(100, occ, 10)
    assert p is not None
    assert p.start_cm == 50


def test_no_space():
    occ = [Segment(0, 80)]
    assert first_fit(100, occ, 25) is None


def test_free_gaps_edges():
    gaps = free_gaps(50, [Segment(10, 20), Segment(30, 35)])
    assert gaps == [Segment(0, 10), Segment(20, 30), Segment(35, 50)]


def test_skips_rail_when_garment_exceeds_length_cap():
    # 杆内空余充足，但衣长超过该杆可收衣长上限 → 必须跳过该杆
    occ: list[Segment] = []
    assert first_fit(200, occ, 90, max_garment_cm=80) is None


def test_garment_equal_to_cap_fits():
    p = first_fit(200, [], 80, max_garment_cm=80)
    assert p is not None
    assert p.end_cm == 80


def test_no_cap_allows_long_garment():
    # 未配置上限的杆不限制衣长
    p = first_fit(200, [], 150)
    assert p is not None
    assert p.start_cm == 0
    assert p.end_cm == 150

    p_explicit_none = first_fit(200, [], 150, max_garment_cm=None)
    assert p_explicit_none is not None
