"""Domain-specific exceptions."""


class ConfigurationError(ValueError):
    """Raised when governed configuration is incomplete or invalid."""


class DataQualityError(RuntimeError):
    """Raised when required pipeline data controls fail."""
