import pytest
from pathlib import Path
import os
from PIL import Image
from rpiweather.display.epaper import (
    IT8951Display,
    MockEpdDriver,
    create_test_display,
    compare_display_image,
)
from rpiweather.settings import RefreshMode


class TestIT8951Display:
    def test_init_simulation_mode(self):
        """Test that IT8951Display initializes in simulation mode."""
        display = IT8951Display(simulate=True)
        assert display.simulate is True
        assert display._epd is None

    def test_init_with_mock_driver(self):
        """Test that IT8951Display initializes with a mock driver."""
        mock_driver = MockEpdDriver()
        display = IT8951Display(simulate=False, epd_driver=mock_driver)

        assert display.simulate is False
        assert display._epd is mock_driver

    def test_get_dimensions(self):
        """Test that get_dimensions returns the configured dimensions."""
        display = IT8951Display(simulate=True)
        width, height = display.get_dimensions()

        assert width == 1872  # Default width
        assert height == 1404  # Default height

    def test_display_image_simulation(self):
        """Test display_image in simulation mode."""
        display = IT8951Display(simulate=True)
        test_path = Path("image.png")

        display.display_image(test_path, RefreshMode.FULL)

        assert display._last_displayed_image == test_path
        assert display._last_refresh_mode == RefreshMode.FULL

    def test_clear_simulation(self):
        """Test clear in simulation mode."""
        display = IT8951Display(simulate=True)

        display.clear()

        assert display._clear_called is True

    def test_test_state_tracking(self):
        """Test the test state tracking methods."""
        display = IT8951Display(simulate=True)
        test_path = Path("image.png")

        # Initially all state should be default
        assert display.get_last_displayed_image() is None
        assert display.get_last_refresh_mode() is None
        assert display.was_clear_called() is False

        # After operations, state should be updated
        display.display_image(test_path, RefreshMode.FULL)
        display.clear()

        # Don't check exact path equality since it's a temp file that may be deleted
        assert display.get_last_displayed_image() is not None
        assert display.get_last_refresh_mode() == RefreshMode.FULL
        assert display.was_clear_called() is True

        # After reset, state should be cleared
        display.reset_test_state()

        assert display.get_last_displayed_image() is None
        assert display.get_last_refresh_mode() is None
        assert display.was_clear_called() is False


class TestMockEpdDriver:
    def test_init_method(self):
        """Test that init method is recorded."""
        driver = MockEpdDriver()

        driver.init()

        assert len(driver.calls) == 1
        assert driver.calls[0]["method"] == "init"

    def test_sleep_method(self):
        """Test that sleep method is recorded."""
        driver = MockEpdDriver()

        driver.sleep()

        assert len(driver.calls) == 1
        assert driver.calls[0]["method"] == "sleep"

    def test_clear_method(self):
        """Test that Clear method is recorded."""
        driver = MockEpdDriver()

        driver.Clear()

        assert len(driver.calls) == 1
        assert driver.calls[0]["method"] == "Clear"

    def test_display_method(self):
        """Test that display method is recorded with parameters."""
        driver = MockEpdDriver()
        test_path = "image.png"

        driver.display(test_path, ROTATE_0=True, mode=2)

        assert len(driver.calls) == 1
        assert driver.calls[0]["method"] == "display"
        assert driver.calls[0]["image_path"] == test_path
        assert driver.calls[0]["ROTATE_0"] is True
        assert driver.calls[0]["mode"] == 2

    def test_set_vcom_method(self):
        """Test that set_vcom method is recorded with parameters."""
        driver = MockEpdDriver()

        driver.set_vcom(1000)

        assert len(driver.calls) == 1
        assert driver.calls[0]["method"] == "set_vcom"
        assert driver.calls[0]["vcom"] == 1000

    def test_get_vcom_method(self):
        """Test that get_vcom method is recorded and returns expected value."""
        driver = MockEpdDriver()

        result = driver.get_vcom()

        assert len(driver.calls) == 1
        assert driver.calls[0]["method"] == "get_vcom"
        assert result == 1000  # Default mock value

    def test_reset_calls(self):
        """Test that reset_calls clears the call history."""
        driver = MockEpdDriver()

        driver.init()
        driver.display("/test/image.png")
        assert len(driver.calls) == 2

        driver.reset_calls()
        assert len(driver.calls) == 0


class TestCreateTestDisplay:
    def test_create_simulated_display(self):
        """Test create_test_display in simulation mode."""
        display = create_test_display(simulate=True)

        assert isinstance(display, IT8951Display)
        assert display.simulate is True
        assert display._epd is None

    def test_create_mock_driver_display(self):
        """Test create_test_display with mock driver."""
        display = create_test_display(simulate=False)

        assert isinstance(display, IT8951Display)
        assert display.simulate is False
        assert isinstance(display._epd, MockEpdDriver)


class TestCompareDisplayImage:
    def test_compare_display_image_no_last_image(self):
        """Test compare_display_image when no image was displayed."""
        display = IT8951Display(simulate=True)

        result = compare_display_image(display, Path("/test/expected.png"))

        assert result is False

    def test_compare_display_image_file_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Test compare_display_image when the last image file doesn't exist."""
        display = IT8951Display(simulate=True)
        display._last_displayed_image = Path("/nonexistent/path.png")

        def mock_exists(path: str | os.PathLike[str]) -> bool:
            return False

        monkeypatch.setattr(os.path, "exists", mock_exists)

        result = compare_display_image(display, Path("/test/expected.png"))

        assert result is False

    @pytest.mark.parametrize("same_content", [True, False])
    def test_compare_display_image_with_files(self, tmp_path: Path, same_content: bool):
        """Test compare_display_image with actual image files."""
        # Create two image files
        display = IT8951Display(simulate=True)

        # Create a last displayed image
        last_path: Path = tmp_path / "last.png"
        last_image = Image.new("L", (100, 100), 255 if same_content else 0)
        last_image.save(last_path)
        display._last_displayed_image = last_path

        # Create an expected image
        expected_path: Path = tmp_path / "expected.png"
        expected_image = Image.new("L", (100, 100), 255)  # White image
        expected_image.save(expected_path)

        result = compare_display_image(display, expected_path)

        assert result is same_content

    def test_compare_display_image_different_modes(self, tmp_path: Path):
        """Test compare_display_image with images in different modes."""
        display = IT8951Display(simulate=True)

        # Create a grayscale last displayed image
        last_path: Path = tmp_path / "last.png"
        last_image = Image.new("L", (100, 100), 255)  # White grayscale
        last_image.save(last_path)
        display._last_displayed_image = last_path

        # Create an RGB expected image (also white)
        expected_path: Path = tmp_path / "expected.png"
        expected_image = Image.new("RGB", (100, 100), (255, 255, 255))
        expected_image.save(expected_path)

        result = compare_display_image(display, expected_path)

        assert result is True  # Mode conversion should make them match

    def test_compare_display_image_different_sizes(self, tmp_path: Path):
        """Test compare_display_image with images of different sizes."""
        display = IT8951Display(simulate=True)

        # Create a small last displayed image
        last_path: Path = tmp_path / "last.png"
        last_image = Image.new("L", (100, 100), 255)  # White, 100x100
        last_image.save(last_path)
        display._last_displayed_image = last_path

        # Create a larger expected image (also white)
        expected_path: Path = tmp_path / "expected.png"
        expected_image = Image.new("L", (200, 200), 255)  # White, 200x200
        expected_image.save(expected_path)

        result = compare_display_image(display, expected_path)

        assert result is True  # Resizing should make them match
