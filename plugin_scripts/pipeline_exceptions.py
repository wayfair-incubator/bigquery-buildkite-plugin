class MissingConfigError(ValueError):
    """Raised when required configuration is missing."""

    pass


class DatasetSchemaDirectoryNonExistent(Exception):
    pass


class DeployFailed(Exception):
    pass
