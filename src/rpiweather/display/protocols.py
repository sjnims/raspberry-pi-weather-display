# src/rpiweather/display/protocols.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from rpiweather.settings.application import RefreshMode


class HtmlRenderer(Protocol):
    """Protocol defining the interface for HTML renderers.

    Implementations of this protocol must provide a method to render
    HTML content to an image file at a specified path.
    """

    def render_to_image(self, html: str, output_path: Path) -> None:
        """Render HTML to an image.

        Args:
            html: HTML content to render
            output_path: Path where the image will be saved
        """
        ...


@runtime_checkable
class Display(Protocol):
    """Protocol defining the interface for display devices.

    This protocol abstracts the hardware-specific details of different display
    technologies (e-ink, LCD, etc.) to allow the application to work with
    any compatible display driver.

    Runtime checking allows the application to detect if an object implements
    this protocol at runtime rather than just during type checking.
    """

    def display_image(self, image_path: Path, mode: RefreshMode = RefreshMode.GREYSCALE) -> None:
        """Display an image on the device.

        Args:
            image_path: Path to the image file
            mode: RefreshMode
                Which refresh mode to use (FULL or GREYSCALE)
        """
        ...

    def get_dimensions(self) -> tuple[int, int]:
        """Return the width and height of the display in pixels.

        Returns:
            Tuple of (width, height) in pixels
        """
        ...

    def clear(self) -> None:
        """Clear the display to white."""
        ...


# Alias for the display protocol, for clearer DI naming
DisplayDriver = Display


class MockHtmlRenderer:
    """Mock implementation of HtmlRenderer for testing."""

    def __init__(self):
        self.render_calls: list[dict[str, object]] = []

    def render_to_image(self, html: str, output_path: Path, create_file: bool = True) -> None:
        """Record the render call without actually rendering.

        Args:
            html: HTML content to render
            output_path: Path where the image would be saved
            create_file: If True, create an empty file at output_path
        """
        self.render_calls.append({"html": html, "output_path": output_path})

        # Only create the file if requested and it's not in a test path
        if create_file and not str(output_path).startswith("/test"):
            # Create parent directories if they don't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Create an empty file
            output_path.touch()

    def reset_call_history(self) -> None:
        """Reset the call history for testing."""
        self.render_calls = []


class MockDisplay:
    """Mock implementation of Display for testing."""

    def __init__(self):
        self.display_calls: list[dict[str, object]] = []
        self.clear_calls: list[dict[str, object]] = []

    def display_image(self, image_path: Path, mode: RefreshMode = RefreshMode.GREYSCALE) -> None:
        """Record the display call without requiring hardware."""
        self.display_calls.append({"image_path": image_path, "mode": mode})

    def get_dimensions(self) -> tuple[int, int]:
        """Mock implementation - return a default size."""
        return (800, 600)

    def clear(self) -> None:
        """Mock implementation of clear method."""
        self.clear_calls.append({})

    def reset_call_history(self) -> None:
        """Reset the call history for testing."""
        self.display_calls = []
        self.clear_calls = []


class ErrorSimulatingDisplay(MockDisplay):
    """Display mock that can simulate hardware errors."""

    def __init__(self, fail_on_methods: list[str] | None = None):
        """Initialize with optional methods that should fail.

        Args:
            fail_on_methods: List of method names that should raise exceptions
        """
        super().__init__()
        self.fail_on_methods = fail_on_methods or []

    def display_image(self, image_path: Path, mode: RefreshMode = RefreshMode.GREYSCALE) -> None:
        """Either record the call or raise an exception based on configuration."""
        if "display_image" in self.fail_on_methods:
            raise RuntimeError("Simulated display hardware failure")
        super().display_image(image_path, mode)

    def clear(self) -> None:
        """Either record the call or raise an exception based on configuration."""
        if "clear" in self.fail_on_methods:
            raise RuntimeError("Simulated display hardware failure")
        super().clear()

    def get_dimensions(self) -> tuple[int, int]:
        """Either return dimensions or raise an exception based on configuration."""
        if "get_dimensions" in self.fail_on_methods:
            raise RuntimeError("Simulated display hardware failure")
        return super().get_dimensions()


def create_mock_html_renderer() -> MockHtmlRenderer:
    """Create and return a mock HTML renderer for testing."""
    return MockHtmlRenderer()


def create_mock_display() -> MockDisplay:
    """Create and return a mock display for testing."""
    return MockDisplay()


def create_error_simulating_display(
    fail_on_methods: list[str] | None = None,
) -> ErrorSimulatingDisplay:
    """Create a display that will fail on specified methods."""
    return ErrorSimulatingDisplay(fail_on_methods)


def assert_display_called_with(
    mock_display: MockDisplay,
    expected_image_path: Path,
    expected_mode: RefreshMode = RefreshMode.GREYSCALE,
) -> bool:
    """Assert that display was called with expected parameters.

    Args:
        mock_display: The mock display instance
        expected_image_path: The expected image path
        expected_mode: The expected refresh mode

    Returns:
        True if the assertion passes, raises AssertionError otherwise
    """
    assert len(mock_display.display_calls) > 0, "Display was not called"
    last_call = mock_display.display_calls[-1]
    assert last_call["image_path"] == expected_image_path, (
        f"Expected {expected_image_path}, got {last_call['image_path']}"
    )
    assert last_call["mode"] == expected_mode, (
        f"Expected mode {expected_mode}, got {last_call['mode']}"
    )
    return True


def assert_html_renderer_called_with(
    mock_renderer: MockHtmlRenderer,
    expected_html: str | None = None,
    expected_output_path: Path | None = None,
) -> bool:
    """Assert that HTML renderer was called with expected parameters.

    Args:
        mock_renderer: The mock renderer instance
        expected_html: Expected HTML content (can be None to skip check)
        expected_output_path: Expected output path (can be None to skip check)

    Returns:
        True if the assertion passes, raises AssertionError otherwise
    """
    assert len(mock_renderer.render_calls) > 0, "HTML renderer was not called"
    last_call = mock_renderer.render_calls[-1]

    if expected_html is not None:
        assert last_call["html"] == expected_html, (
            f"Expected HTML: {expected_html}, got {last_call['html']}"
        )

    if expected_output_path is not None:
        assert last_call["output_path"] == expected_output_path, (
            f"Expected path: {expected_output_path}, got {last_call['output_path']}"
        )

    return True


def assert_display_cleared(mock_display: MockDisplay) -> bool:
    """Assert that the display's clear method was called.

    Args:
        mock_display: The mock display instance

    Returns:
        True if the assertion passes, raises AssertionError otherwise
    """
    assert len(mock_display.clear_calls) > 0, "Display clear method was not called"
    return True


class TemplateProtocol(Protocol):
    """Protocol defining the expected interface for templates.

    This protocol abstracts the Jinja2 Template interface to allow
    for proper type checking of template operations.
    """

    def render(self, **kwargs: Any) -> str:
        """Render a template with the given context variables.

        Args:
            **kwargs: Template context variables

        Returns:
            Rendered template as a string
        """
        ...
