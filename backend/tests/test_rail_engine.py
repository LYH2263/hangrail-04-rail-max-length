from app.services.rail_engine import Placement, Segment, first_fit, free_gaps


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


def test_garment_over_limit_skips_rail_even_with_space():
    # 杆上空余充足（无占位），但衣长 90 超过上限 80，必须跳过
    p = first_fit(200, [], 90, max_garment_length_cm=80)
    assert p is None


def test_garment_at_limit_fits():
    p = first_fit(200, [], 80, max_garment_length_cm=80)
    assert p == Placement(0, 80)


def test_no_limit_allows_long_garment():
    # 未配置上限的杆不限制衣长，长衣可正常上杆
    p = first_fit(200, [], 90, max_garment_length_cm=None)
    assert p == Placement(0, 90)
