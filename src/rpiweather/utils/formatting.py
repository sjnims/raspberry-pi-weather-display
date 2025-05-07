"""Text and number formatting utilities."""

from __future__ import annotations


def format_temperature(temp: float, unit: str = "°F") -> str:
    """Format temperature value with unit.

    Args:
        temp: Temperature value
        unit: Temperature unit

    Returns:
        Formatted temperature string
    """
    return f"{round(temp)}{unit}"


def format_percentage(value: float) -> str:
    """Format value as percentage.

    Args:
        value: Value to format (0-1)

    Returns:
        Formatted percentage string
    """
    return f"{round(value * 100)}%"
