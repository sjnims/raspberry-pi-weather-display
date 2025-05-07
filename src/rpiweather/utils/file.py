"""File utility functions."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Final

logger: Final = logging.getLogger(__name__)


def ensure_directory_exists(directory: Path) -> None:
    """Create directory if it doesn't exist.

    Args:
        directory: Path to create
    """
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug("Created directory: %s", directory)


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes.

    Args:
        file_path: Path to file

    Returns:
        File size in bytes
    """
    if not file_path.exists():
        return 0
    return os.path.getsize(file_path)
