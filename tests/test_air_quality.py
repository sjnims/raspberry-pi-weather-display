import pytest

from rpiweather.weather.air_quality import AirQuality


def test_from_aqi_value_maps_label() -> None:
    aqi = AirQuality.from_aqi_value(3)
    assert aqi.aqi == "Moderate"
    assert aqi.aqi_value == 3
    assert aqi.components is None


def test_from_aqi_value_raises_on_invalid() -> None:
    with pytest.raises(ValueError):
        AirQuality.from_aqi_value(0)
    with pytest.raises(ValueError):
        AirQuality.from_aqi_value(6)


def test_not_available_creates_fallback() -> None:
    aqi = AirQuality.not_available()
    assert aqi.aqi == "N/A"
    assert aqi.aqi_value == 1
    assert aqi.components is None


def test_description_includes_aqi() -> None:
    aqi = AirQuality(aqi="Good", aqi_value=1, components=None)
    assert "Good" in aqi.description
    assert "1" in aqi.description


def test_color_for_known_and_unknown_values() -> None:
    known = AirQuality(aqi="Good", aqi_value=1, components=None)
    assert known.color.startswith("#")

    unknown = AirQuality(aqi="Mystery", aqi_value=5, components=None)
    assert unknown.color == AirQuality.AQI_COLORS[5]
