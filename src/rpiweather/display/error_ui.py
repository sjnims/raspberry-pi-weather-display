"""UI generation for error screens on the e-ink display."""

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

from jinja2 import Template

from rpiweather.display.epaper import IT8951Display
from rpiweather.display.protocols import DisplayDriver, TemplateProtocol
from rpiweather.settings.application import RefreshMode
from rpiweather.system.status import SystemStatus


class HtmlRenderer(Protocol):
    """Protocol for HTML to image rendering."""

    def render_to_image(self, html: str, output_path: Path) -> None:
        """Render HTML to an image file.

        Args:
            html: HTML content to render
            output_path: Path where the image will be saved
        """
        ...


class ErrorRenderer:
    """Renderer for error screens on the e-ink display."""

    # Error screen template using Jinja2 syntax
    ERROR_TEMPLATE = """<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Weather Display Error</title>
        <link rel="stylesheet" href="/static/css/style.css">
        <style>
            body {
                font-family: 'Atkinson', sans-serif;
                text-align: center;
                padding: 40px;
                background-color: white;
                color: black;
            }
            .error-container {
                border: 3px solid black;
                border-radius: 15px;
                padding: 30px;
                margin: 40px auto;
                max-width: 80%;
            }
            .error-title {
                font-size: 42px;
                margin-bottom: 20px;
                font-weight: bold;
            }
            .error-message {
                font-size: 28px;
                margin-bottom: 30px;
            }
            .error-time {
                font-size: 24px;
                margin-bottom: 20px;
                font-style: italic;
            }
            .retry-info {
                font-size: 22px;
                margin-top: 30px;
            }
            .battery-info {
                position: absolute;
                top: 20px;
                right: 20px;
                font-size: 24px;
            }
        </style>
    </head>
    <body>
        <div class="battery-info">
            Battery: {{ system_status.soc }}%{{ " ⚡" if system_status.is_charging else "" }}
        </div>
        <div class="error-container">
            <div class="error-title">Weather Update Failed</div>
            <div class="error-message">{{ error_message }}</div>
            <div class="error-time">Last attempt: {{ timestamp }}</div>
            <div class="retry-info">The system will automatically retry later.</div>
        </div>
    </body>
    </html>"""

    def __init__(
        self,
        html_renderer: HtmlRenderer,
        display_driver: DisplayDriver | None = None,
        template: str | None = None,
    ) -> None:
        """Initialize the error renderer.

        Args:
            html_renderer: Renderer to convert HTML to images
            display_driver: Display device (creates default if None)
            template: Custom error template (uses default if None)
        """
        self.html_renderer = html_renderer
        self.display_driver = display_driver or IT8951Display()
        self.template = Template(template or self.ERROR_TEMPLATE)

    def render_error(
        self,
        error_message: str,
        system_status: SystemStatus,
        output_path: Path,
        display_immediately: bool = False,
    ) -> None:
        """Render an error message to image and optionally display it.

        Args:
            error_message: Error message to display
            system_status: System status information
            output_path: Path to save the rendered image
            display_immediately: Whether to display the image immediately
        """
        # Create template from the template string
        template = Template(self.ERROR_TEMPLATE)

        # More explicitly cast the template to the Protocol type
        typed_template = cast(TemplateProtocol, template)

        # Create context with current timestamp
        context = {
            "error_message": error_message,
            "system_status": system_status,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        typed_context: dict[str, Any] = context

        # Render template to HTML
        html_content = typed_template.render(**typed_context)

        # Convert to image
        self.html_renderer.render_to_image(html_content, output_path)

        # Display if requested
        if display_immediately:
            self.display_driver.display_image(output_path, mode=RefreshMode.GREYSCALE)
