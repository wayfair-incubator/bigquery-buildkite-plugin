import pytest

from plugin_scripts.exceptions import (
    DatasetSchemaNonExistent,
    DeployFailed,
)


@pytest.mark.parametrize(
    "exception_object",
    [
        DatasetSchemaNonExistent({}),
        DeployFailed({}),
    ],
)
def test_exception_init(exception_object):
    e = exception_object
    assert isinstance(e, Exception)


@pytest.mark.parametrize(
    "exception_class",
    [
        DatasetSchemaNonExistent,
        DeployFailed,
    ],
)
def test_exception_throws(exception_class):
    e = exception_class({})
    with pytest.raises(exception_class):
        raise e
