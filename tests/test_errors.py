import pytest
from rpiweather.weather.errors import (
    WeatherAPIError,
    NetworkError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ClientError,
    ServerError,
    ParseError,
)


def test_weather_api_error_str_and_flags() -> None:
    err = WeatherAPIError(code=404, message="Not Found")
    assert str(err) == "[404] Not Found"
    assert err.is_client_error is True
    assert err.is_server_error is False


@pytest.mark.parametrize(
    "code, expected_type",
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, NotFoundError),
        (429, RateLimitError),
        (400, ClientError),
        (500, ServerError),
        (999, WeatherAPIError),
    ],
)
def test_from_response_creates_expected_error(
    code: int, expected_type: type[WeatherAPIError]
) -> None:
    resp = {"message": "test error"}
    err = WeatherAPIError.from_response(resp, code)
    assert isinstance(err, expected_type)
    assert err.code == code
    assert "test error" in str(err)


def test_network_error_wraps_exception() -> None:
    try:
        raise ConnectionError("BOOM")
    except ConnectionError as e:
        err = NetworkError(message="Connection error", original_error=e)
        assert isinstance(err, NetworkError)
        assert str(err) == "[0] Connection error"
        assert isinstance(err.original_error, Exception)


def test_parse_error_wraps_exception() -> None:
    try:
        raise ValueError("bad parse")
    except ValueError as e:
        err = ParseError(message="Parse error", original_error=e)
        assert isinstance(err, ParseError)
        assert str(err) == "[0] Parse error"
        assert isinstance(err.original_error, Exception)
