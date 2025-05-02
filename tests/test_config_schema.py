from pathlib import Path

import pytest
from rpiweather.config import WeatherConfig


GOOD_YAML = """
lat: 45.0
lon: -93.0
city: Testville
api_key: abcdef123456
units: imperial
"""

BAD_YAML = """
lat: 45.0
lon: -93.0
city: Testville
api_key: short
units: imperial
"""


def test_valid_config(tmp_path: Path):
    cfg_file = tmp_path / "good.yaml"
    cfg_file.write_text(GOOD_YAML)
    cfg = WeatherConfig.load(cfg_file)
    assert isinstance(cfg, WeatherConfig)
    assert cfg.city == "Testville"


def test_invalid_config(tmp_path: Path):
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text(BAD_YAML)
    with pytest.raises(RuntimeError):
        WeatherConfig.load(cfg_file)
