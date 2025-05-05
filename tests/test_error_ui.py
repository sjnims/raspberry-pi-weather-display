from pathlib import Path
from unittest.mock import Mock

import pytest

from rpiweather.display.error_ui import ErrorRenderer
from rpiweather.display.protocols import RefreshMode
from rpiweather.system.status import SystemStatus


@pytest.fixture
def mock_renderer() -> Mock:
    return Mock()


@pytest.fixture
def mock_display() -> Mock:
    return Mock()


def test_error_renderer_saves_image_only(
    tmp_path: Path, mock_renderer: Mock, mock_display: Mock
) -> None:
    error = ErrorRenderer(html_renderer=mock_renderer, display_driver=mock_display)
    output_path = tmp_path / "error_output.png"

    status = SystemStatus(soc=5, is_charging=False)
    error.render_error(
        "Sample error",
        system_status=status,
        output_path=output_path,
        display_immediately=False,
    )

    mock_renderer.render_to_image.assert_called_once()
    mock_display.display_image.assert_not_called()


def test_error_renderer_displays_image(
    tmp_path: Path, mock_renderer: Mock, mock_display: Mock
) -> None:
    error = ErrorRenderer(html_renderer=mock_renderer, display_driver=mock_display)
    output_path = tmp_path / "error_output.png"

    status = SystemStatus(soc=20, is_charging=True)
    error.render_error(
        "Rendering failed",
        system_status=status,
        output_path=output_path,
        display_immediately=True,
    )

    mock_renderer.render_to_image.assert_called_once()
    mock_display.display_image.assert_called_once_with(
        output_path, mode=RefreshMode.GREYSCALE
    )
