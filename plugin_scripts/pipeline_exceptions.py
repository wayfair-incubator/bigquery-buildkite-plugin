class MissingConfigError(ValueError):
    """Raised when required configuration is missing."""

    pass


class DatasetSchemaDirectoryNonExistent(Exception):
    pass


class DeployFailed(Exception):
    pass


class PlanViolation(Exception):
    """Raised if plan mode would send a request that could change something."""
