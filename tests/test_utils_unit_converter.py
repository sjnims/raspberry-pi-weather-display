import pytest
from rpiweather.weather.utils.units import UnitConverter


@pytest.mark.parametrize("mm, expected", [(25.4, 1.0), (0.0, 0.0), (12.7, 0.5)])
def test_mm_to_inches(mm: float, expected: float) -> None:
    assert UnitConverter.mm_to_inches(mm) == expected


@pytest.mark.parametrize("hpa, expected", [(1013.25, 29.92), (1000.0, 29.53)])
def test_hpa_to_inhg(hpa: float, expected: float) -> None:
    assert UnitConverter.hpa_to_inhg(hpa) == expected


@pytest.mark.parametrize(
    "deg, expected",
    [
        (0, "N"),
        (45, "NE"),
        (90, "E"),
        (135, "SE"),
        (180, "S"),
        (225, "SW"),
        (270, "W"),
        (315, "NW"),
        (359, "N"),
    ],
)
def test_deg_to_cardinal(deg: float, expected: str) -> None:
    assert UnitConverter.deg_to_cardinal(deg) == expected


@pytest.mark.parametrize(
    "mph, expected_bft",
    [
        (0.5, 0),
        (1.0, 1),
        (4.0, 2),
        (7.0, 3),
        (12.0, 4),
        (18.0, 5),
        (24.0, 6),
        (31.0, 7),
        (38.0, 8),
        (46.0, 9),
        (54.0, 10),
        (63.0, 11),
        (73.0, 12),
        (90.0, 12),  # Beyond scale
    ],
)
def test_beaufort_from_speed(mph: float, expected_bft: int) -> None:
    assert UnitConverter.beaufort_from_speed(mph) == expected_bft
