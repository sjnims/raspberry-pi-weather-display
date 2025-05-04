import pytest
from pathlib import Path
from rpiweather.display.protocols import (
    MockDisplay,
    MockHtmlRenderer,
    ErrorSimulatingDisplay,
    create_mock_display,
    create_mock_html_renderer,
    create_error_simulating_display,
    assert_display_called_with,
    assert_html_renderer_called_with,
    assert_display_cleared,
)
from rpiweather.settings import RefreshMode


class TestMockDisplay:
    def test_display_image_tracking(self):
        """Test that display_image calls are properly tracked."""
        display = MockDisplay()
        test_path = Path("image.png")

        display.display_image(test_path, RefreshMode.FULL)

        assert len(display.display_calls) == 1
        assert display.display_calls[0]["image_path"] == test_path
        assert display.display_calls[0]["mode"] == RefreshMode.FULL

    def test_clear_tracking(self):
        """Test that clear() calls are properly tracked."""
        display = MockDisplay()

        display.clear()

        assert len(display.clear_calls) == 1

    def test_get_dimensions(self):
        """Test that get_dimensions returns expected values."""
        display = MockDisplay()
        dimensions = display.get_dimensions()

        assert isinstance(dimensions, tuple)
        assert len(dimensions) == 2
        assert all(isinstance(dim, int) for dim in dimensions)

    def test_reset_call_history(self):
        """Test that reset_call_history clears all tracked calls."""
        display = MockDisplay()

        display.display_image(Path("/test/image.png"))
        display.clear()
        assert len(display.display_calls) == 1
        assert len(display.clear_calls) == 1

        display.reset_call_history()
        assert len(display.display_calls) == 0
        assert len(display.clear_calls) == 0


class TestMockHtmlRenderer:
    def test_render_to_image_tracking(self, tmp_path: Path):
        """Test that render_to_image calls are properly tracked."""
        renderer = MockHtmlRenderer()
        test_html = "<html>Test</html>"
        test_path = tmp_path / "test_output.png"

        # Skip file creation since we're just testing call tracking
        renderer.render_to_image(test_html, test_path, create_file=False)

        assert len(renderer.render_calls) == 1
        assert renderer.render_calls[0]["html"] == test_html
        assert renderer.render_calls[0]["output_path"] == test_path

    def test_file_creation(self, tmp_path: Path):
        """Test that render_to_image creates a file."""
        renderer = MockHtmlRenderer()
        test_path = tmp_path / "output.png"

        # Explicitly set create_file=True since we're testing file creation
        renderer.render_to_image("<html></html>", test_path, create_file=True)

        assert test_path.exists()

    def test_reset_call_history(self, tmp_path: Path):
        """Test that reset_call_history clears tracked calls."""
        renderer = MockHtmlRenderer()
        test_path = tmp_path / "output.png"

        # Skip file creation since we're just testing call tracking
        renderer.render_to_image("<html></html>", test_path, create_file=False)
        assert len(renderer.render_calls) == 1

        renderer.reset_call_history()
        assert len(renderer.render_calls) == 0


class TestErrorSimulatingDisplay:
    def test_non_failing_methods(self):
        """Test that methods work normally when not configured to fail."""
        display = ErrorSimulatingDisplay()
        test_path = Path("image.png")

        # These should not raise exceptions
        display.display_image(test_path)
        display.clear()
        display.get_dimensions()

        assert len(display.display_calls) == 1
        assert len(display.clear_calls) == 1

    def test_failing_display_image(self):
        """Test that display_image raises when configured to fail."""
        display = ErrorSimulatingDisplay(fail_on_methods=["display_image"])

        with pytest.raises(RuntimeError) as excinfo:
            display.display_image(Path("/test/image.png"))

        assert "Simulated display hardware failure" in str(excinfo.value)
        assert len(display.display_calls) == 0  # Call should not be recorded

    def test_failing_clear(self):
        """Test that clear raises when configured to fail."""
        display = ErrorSimulatingDisplay(fail_on_methods=["clear"])

        with pytest.raises(RuntimeError) as excinfo:
            display.clear()

        assert "Simulated display hardware failure" in str(excinfo.value)
        assert len(display.clear_calls) == 0  # Call should not be recorded

    def test_failing_get_dimensions(self):
        """Test that get_dimensions raises when configured to fail."""
        display = ErrorSimulatingDisplay(fail_on_methods=["get_dimensions"])

        with pytest.raises(RuntimeError) as excinfo:
            display.get_dimensions()

        assert "Simulated display hardware failure" in str(excinfo.value)


class TestFactoryFunctions:
    def test_create_mock_display(self):
        """Test that create_mock_display returns a MockDisplay instance."""
        display = create_mock_display()
        assert isinstance(display, MockDisplay)

    def test_create_mock_html_renderer(self):
        """Test that create_mock_html_renderer returns a MockHtmlRenderer."""
        renderer = create_mock_html_renderer()
        assert isinstance(renderer, MockHtmlRenderer)

    def test_create_error_simulating_display(self):
        """Test that create_error_simulating_display returns an ErrorSimulatingDisplay."""
        display = create_error_simulating_display(["display_image"])
        assert isinstance(display, ErrorSimulatingDisplay)
        assert "display_image" in display.fail_on_methods


class TestAssertionHelpers:
    def test_assert_display_called_with_success(self):
        """Test that assert_display_called_with passes with matching parameters."""
        display = MockDisplay()
        test_path = Path("image.png")

        display.display_image(test_path, RefreshMode.FULL)

        result = assert_display_called_with(display, test_path, RefreshMode.FULL)
        assert result is True

    def test_assert_display_called_with_failure_no_calls(self):
        """Test that assert_display_called_with fails when no calls were made."""
        display = MockDisplay()

        with pytest.raises(AssertionError) as excinfo:
            assert_display_called_with(display, Path("/test/image.png"))

        assert "Display was not called" in str(excinfo.value)

    def test_assert_display_called_with_failure_wrong_path(self):
        """Test that assert_display_called_with fails with wrong path."""
        display = MockDisplay()
        display.display_image(Path("/actual/path.png"))

        with pytest.raises(AssertionError) as excinfo:
            assert_display_called_with(display, Path("/expected/path.png"))

        assert "Expected" in str(excinfo.value)

    def test_assert_html_renderer_called_with_success(self, tmp_path: Path):
        """Test that assert_html_renderer_called_with passes with matching parameters."""
        renderer = MockHtmlRenderer()
        test_html = "<html>Test</html>"
        test_path = tmp_path / "output.png"

        # Skip file creation since we're just testing assertions
        renderer.render_to_image(test_html, test_path, create_file=False)

        result = assert_html_renderer_called_with(renderer, test_html, test_path)
        assert result is True

    def test_assert_html_renderer_called_with_partial_match(self, tmp_path: Path):
        """Test that assert_html_renderer_called_with works with partial parameters."""
        renderer = MockHtmlRenderer()
        test_html = "<html>Test</html>"
        test_path = tmp_path / "output.png"

        # Skip file creation since we're just testing assertions
        renderer.render_to_image(test_html, test_path, create_file=False)

        # Should pass with only html specified
        result1 = assert_html_renderer_called_with(renderer, expected_html=test_html)
        assert result1 is True

        # Should pass with only path specified
        result2 = assert_html_renderer_called_with(
            renderer, expected_output_path=test_path
        )
        assert result2 is True

    def test_assert_display_cleared_success(self):
        """Test that assert_display_cleared passes when clear was called."""
        display = MockDisplay()
        display.clear()

        result = assert_display_cleared(display)
        assert result is True

    def test_assert_display_cleared_failure(self):
        """Test that assert_display_cleared fails when clear was not called."""
        display = MockDisplay()

        with pytest.raises(AssertionError) as excinfo:
            assert_display_cleared(display)

        assert "Display clear method was not called" in str(excinfo.value)
