from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel, field_validator

from rpiweather.utils.time import TimeUtils

ValidatorCallable = Callable[[type[Any], Any], Any]

T = TypeVar("T", bound="TimeStampModel")


class TimeStampModel(BaseModel):
    """Base model with timestamp conversion utilities.

    This class serves as a base for models that need to convert UNIX timestamps
    to datetime objects with consistent timezone handling.
    """

    @classmethod
    def convert_timestamp(cls, v: int) -> datetime:
        """Convert UNIX timestamp to UTC datetime with timezone information.

        Args:
            v: UNIX timestamp (seconds since epoch)

        Returns:
            datetime: Timezone-aware datetime object in UTC
        """
        return TimeUtils.epoch_to_datetime(v)

    @staticmethod
    def timestamp_validator(field_name: str) -> ValidatorCallable:
        """Factory method to create timestamp field validators.

        Args:
            field_name: The field name to validate

        Returns:
            A validator method for the specified field
        """

        @field_validator(field_name, mode="before")
        def validate_timestamp(cls: type[Any], v: Any) -> Any:
            if isinstance(v, int):
                return TimeStampModel.convert_timestamp(v)
            return v

        return validate_timestamp
