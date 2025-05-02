from enum import Enum
from datetime import timedelta

# Preview output directory and filenames
PREVIEW_DIR = "preview"
PREVIEW_HTML_NAME = "dash-preview.html"
PREVIEW_PNG_NAME = "dash.png"

# Default URL for remote stay-awake flag
DEFAULT_STAY_AWAKE_URL = "http://localhost:8000/stay_awake.json"

# Time interval after which to force a full e-ink panel refresh
FULL_REFRESH_INTERVAL: timedelta = timedelta(hours=6)


class RefreshMode(Enum):
    """Enum for e-paper refresh modes."""

    FULL = 0  # full white-black-white refresh
    GREYSCALE = 2  # 16-level greyscale refresh (GC16)
