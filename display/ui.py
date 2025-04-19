"""UI generation functions for the e-ink display."""

from datetime import datetime
from pathlib import Path
from typing import Callable

from display.epaper import display_png


def render_error_screen(
    error_msg: str,
    soc: int,
    is_charging: bool,
    html_to_png_func: Callable[[str, Path], None],
    out_path: Path
) -> None:
    """
    Create and display an error screen when API calls fail.

    Parameters
    ----------
    error_msg : str
        The error message to display.
    soc : int
        Battery state of charge.
    is_charging : bool
        Whether the device is charging.
    html_to_png_func : Callable[[str, Path], None]
        Function to convert HTML to PNG.
    out_path : Path
        Path to save the output PNG.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Create a simple HTML error page
    error_html = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Weather Display Error</title>
        <link rel="stylesheet" href="/static/css/style.css">
        <style>
            body {{
                font-family: 'Atkinson', sans-serif;
                text-align: center;
                padding: 40px;
                background-color: white;
                color: black;
            }}
            .error-container {{
                border: 3px solid black;
                border-radius: 15px;
                padding: 30px;
                margin: 40px auto;
                max-width: 80%;
            }}
            .error-title {{
                font-size: 42px;
                margin-bottom: 20px;
                font-weight: bold;
            }}
            .error-message {{
                font-size: 28px;
                margin-bottom: 30px;
            }}
            .error-time {{
                font-size: 24px;
                margin-bottom: 20px;
                font-style: italic;
            }}
            .retry-info {{
                font-size: 22px;
                margin-top: 30px;
            }}
            .battery-info {{
                position: absolute;
                top: 20px;
                right: 20px;
                font-size: 24px;
            }}
        </style>
    </head>
    <body>
        <div class="battery-info">
            Battery: {soc}%{" ⚡" if is_charging else ""}
        </div>
        <div class="error-container">
            <div class="error-title">Weather Update Failed</div>
            <div class="error-message">{error_msg}</div>
            <div class="error-time">Last attempt: {now}</div>
            <div class="retry-info">The system will automatically retry later.</div>
        </div>
    </body>
    </html>"""

    # Convert HTML to PNG and display it
    html_to_png_func(error_html, out_path)
    display_png(out_path, mode_override=2)  # Using mode 2 (GC16) for error display
