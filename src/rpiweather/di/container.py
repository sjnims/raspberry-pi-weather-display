# src/rpiweather/di/container.py
"""Dependency injection container."""

from __future__ import annotations

from typing import Any, Dict, Optional, Type, TypeVar

T = TypeVar("T")


class ServiceLocator:
    """Service locator pattern implementation."""

    _instance = None
    _services: Dict[str, Any] = {}

    def __new__(cls) -> "ServiceLocator":
        """Singleton implementation."""
        if cls._instance is None:
            cls._instance = super(ServiceLocator, cls).__new__(cls)
        return cls._instance

    def register(self, interface_cls: Type[T], implementation: T) -> None:
        """Register a service implementation.

        Args:
            interface_cls: Interface/class type
            implementation: Implementation instance
        """
        self._services[interface_cls.__name__] = implementation

    def resolve(self, interface_cls: Type[T]) -> Optional[T]:
        """Resolve a service implementation.

        Args:
            interface_cls: Interface/class to resolve

        Returns:
            Instance of the requested service or None if not registered
        """
        return self._services.get(interface_cls.__name__)


# Example usage in application initialization
"""
# Create service locator
container = ServiceLocator()

# Register services
container.register(WeatherAPI, WeatherAPI(config))
container.register(TemplateRenderer, TemplateRenderer())

# Resolve services where needed
weather_api = container.resolve(WeatherAPI)
"""
