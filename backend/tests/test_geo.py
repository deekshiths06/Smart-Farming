import math

from app.services import geo


def test_polygon_area_square_metres():
    # Roughly a 1 km x 1 km square around (0.0, 0.0).
    ring = [[-0.0045, -0.0045], [0.0045, -0.0045], [0.0045, 0.0045], [-0.0045, 0.0045]]
    area = geo.polygon_area_square_metres(ring)
    assert 800_000 < area < 1_150_000, area


def test_polygon_area_known_small_square():
    # 100 m x 100 m near Bangalore. Use the equirectangular expectation as a range.
    lat = 12.97
    ring = [[77.59, lat - 0.0004], [77.59 + 0.001, lat - 0.0004], [77.59 + 0.001, lat + 0.0004], [77.59, lat + 0.0004]]
    area = geo.polygon_area_square_metres(ring)
    dlat_m = 0.0008 * 111_320
    dlon_m = 0.001 * 111_320 * math.cos(math.radians(lat))
    expected = dlat_m * dlon_m
    assert abs(area - expected) / expected < 0.02, (area, expected)


def test_ring_auto_closing_not_required():
    ring = [[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]]
    a1 = geo.polygon_area_square_metres(ring)
    a2 = geo.polygon_area_square_metres(ring[:-1])
    assert abs(a1 - a2) < 1e-6


def test_convert_area():
    assert geo.convert_area(1, "acre", "acre") == 1
    assert abs(geo.convert_area(1, "acre", "hectare") - 0.40468564224) < 1e-9
    assert geo.convert_area(1, "bigha", "acre") is None
    assert geo.area_summary(1, "bigha") is None


def test_area_summary_formats():
    summary = geo.area_summary(1, "acre")
    assert summary["acres"] == 1.0
    assert abs(summary["hectares"] - 0.4047) < 1e-3


if __name__ == "__main__":
    for fn in [t for n, t in sorted(globals().items()) if n.startswith("test_")]:
        fn()
        print("ok", fn.__name__)