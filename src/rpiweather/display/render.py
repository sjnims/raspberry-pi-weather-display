"""Dashboard rendering helpers (Jinja environment, filters, html→png)."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import tempfile
import zoneinfo
from datetime import datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from rpiweather.weather.helpers import (
    deg_to_cardinal,
    moon_phase_icon,
    owm_icon_class,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # repo root

# ─────────────────────────── Jinja ENV ──────────────────────────


ENV = Environment(
    loader=FileSystemLoader(PROJECT_ROOT / "templates"),
    autoescape=select_autoescape(["html"]),
)


def wind_rotation(deg: float, direction: str = "towards") -> float:  # noqa: D401
    """Return adjusted wind bearing for 'from' or 'towards' arrow."""
    return deg if direction == "towards" else (deg + 180) % 360


ENV.filters.update(
    {
        "deg_to_cardinal": deg_to_cardinal,
        "owm_icon": owm_icon_class,
        "moon_phase_icon": moon_phase_icon,
        "wind_rotation": wind_rotation,
    }
)

LOCAL_TZ = zoneinfo.ZoneInfo("America/New_York")
FULL_REFRESH_INTERVAL = timedelta(hours=24)


# ─────────────────────────── Jinja date‑time filters ──────────────────────


def ts_to_local(ts: int) -> datetime:
    """Convert POSIX timestamp to local datetime."""
    return datetime.fromtimestamp(ts, tz=LOCAL_TZ)


def dt_format(d: datetime, fmt: str = "%-I %p") -> str:
    """strftime wrapper usable as a Jinja filter."""
    return d.strftime(fmt)


ENV.filters["ts_to_dt"] = ts_to_local
ENV.filters["strftime"] = dt_format

# load template after all custom filters are registered
TEMPLATE: Template = ENV.get_template("dashboard.html.j2")

# ─────────────────────────── HTML → PNG ─────────────────────────


def html_to_png(html: str, out: Path, preview: bool = False) -> None:
    """
    Render HTML to PNG using wkhtmltoimage (xvfb-run on Linux headless).

    In preview mode on macOS/Windows, open in the default browser instead.
    """
    if preview and platform.system() != "Linux":
        tmpdir = Path(tempfile.mkdtemp())
        shutil.copytree(PROJECT_ROOT / "static", tmpdir / "static", dirs_exist_ok=True)
        html_path = tmpdir / "dash-preview.html"
        html_local = re.sub(r'href="/static/', 'href="static/', html)
        html_path.write_text(html_local, "utf-8")

        import webbrowser  # local import

        webbrowser.open(html_path.as_uri())
        return

    html_path = out.with_suffix(".html")
    html_path.write_text(html, "utf-8")
    cmd = [
        "wkhtmltoimage",
        "--width",
        "1872",
        "--height",
        "1404",
        html_path.as_posix(),
        out.as_posix(),
    ]
    if platform.system() == "Linux":
        cmd = ["xvfb-run", "-a"] + cmd
    subprocess.run(cmd, check=True)
