"""Image manipulation utilities for display rendering."""

from __future__ import annotations

import logging
from typing import Final

logger: Final = logging.getLogger(__name__)


def calculate_dimensions(
    original_width: int, original_height: int, max_width: int, max_height: int
) -> tuple[int, int]:
    """Calculate dimensions while preserving aspect ratio.

    Args:
        original_width: Original image width
        original_height: Original image height
        max_width: Maximum allowed width
        max_height: Maximum allowed height

    Returns:
        Tuple of (width, height) that fits within max dimensions
    """
    ratio = min(max_width / original_width, max_height / original_height)
    return (int(original_width * ratio), int(original_height * ratio))
