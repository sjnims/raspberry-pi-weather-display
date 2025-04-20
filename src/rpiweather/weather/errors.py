# weather/errors.py
class WeatherAPIError(Exception):
    """Uniform wrapper for HTTP or network errors from OpenWeather."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code: int = code
        self.message: str = message
