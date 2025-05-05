from dataclasses import dataclass

import pytest
from pytest import MonkeyPatch

from rpiweather.weather.utils.icons import WeatherIcons


@pytest.mark.parametrize(
    "icon_id, expected",
    [
        ("800d", "wi-day-sunny.svg"),
        ("802n", "wi-night-alt-cloudy.svg"),
        ("999", "wi-na.svg"),  # fallback
    ],
)
def test_get_icon_filename_with_mapping(
    monkeypatch: MonkeyPatch, icon_id: str, expected: str
) -> None:
    monkeypatch.setattr(
        WeatherIcons,
        "_icon_map",
        {"800d": "wi-day-sunny.svg", "802n": "wi-night-alt-cloudy.svg"},
    )

    @dataclass
    class FakeWeather:
        id: int | str
        icon: str

    obj = FakeWeather(id=int(icon_id[:3]), icon=icon_id[3:])
    result = WeatherIcons.get_icon_filename(obj)
    assert result == expected


@pytest.mark.parametrize(
    "phase, expected_icon_suffix",
    [
        (0.00, "new"),
        (0.25, "first-quarter"),
        (0.50, "full"),
        (0.75, "third-quarter"),
        (0.99, "waning-crescent-6"),
    ],
)
def test_get_moon_phase_icon_suffix(phase: float, expected_icon_suffix: str) -> None:
    icon = WeatherIcons.get_moon_phase_icon(phase)
    assert expected_icon_suffix in icon


@pytest.mark.parametrize(
    "phase, label",
    [
        (0.00, "New Moon"),
        (0.12, "Waxing Crescent"),
        (0.25, "First Quarter"),
        (0.37, "Waxing Gibbous"),
        (0.50, "Full Moon"),
        (0.62, "Waning Gibbous"),
        (0.75, "Last Quarter"),
        (0.87, "Waning Crescent"),
    ],
)
def test_get_moon_phase_label(phase: float, label: str) -> None:
    assert WeatherIcons.get_moon_phase_label(phase) == label
