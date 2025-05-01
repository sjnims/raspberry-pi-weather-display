from datetime import datetime, timezone
from typing import Any, Callable, TypeVar, Type
from pydantic import BaseModel, field_validator

# Define a more precise return type for your validator factory
ValidatorCallable = Callable[[Type[Any], Any], Any]

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
        return datetime.fromtimestamp(v, tz=timezone.utc)

    @staticmethod
    def timestamp_validator(field_name: str) -> ValidatorCallable:
        """Factory method to create timestamp field validators.

        Args:
            field_name: The field name to validate

        Returns:
            A validator method for the specified field
        """

        # Define the validator function with proper type annotations
        @field_validator(field_name, mode="before")
        def validate_timestamp(cls: Type[Any], v: Any) -> Any:
            if isinstance(v, int):
                return TimeStampModel.convert_timestamp(v)
            return v

        # Simply return the validator function - no need for cast
        return validate_timestamp
