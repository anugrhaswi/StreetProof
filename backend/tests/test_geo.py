from app.services.geo import haversine_distance, valid_coords


def test_haversine_known_distance():
    # ~111.32 km per degree latitude near equator (approx)
    d = haversine_distance(0.0, 0.0, 1.0, 0.0)
    assert 110_000 < d < 112_000


def test_haversine_zero_distance():
    assert haversine_distance(27.7, 85.3, 27.7, 85.3) == 0.0


def test_haversine_within_radius():
    # ~150m apart
    d = haversine_distance(27.7000, 85.3000, 27.7010, 85.3010)
    assert d < 500
    assert d > 0


def test_valid_coords():
    assert valid_coords(27.7, 85.3) is True
    assert valid_coords(None, 85.3) is False
    assert valid_coords(91, 0) is False
    assert valid_coords(0, 181) is False
