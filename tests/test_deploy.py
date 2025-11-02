import pytest

from plugin_scripts import deploy
from plugin_scripts.deploy import (
    DatasetSchemaDirectoryNonExistent,
    MissingConfigError,
)


@pytest.fixture
def dataset_schema_directory(monkeypatch):
    return monkeypatch.setenv("dataset_schema_directory", "schemas/project")


@pytest.fixture
def gcp_project(monkeypatch):
    return monkeypatch.setenv("gcp_project", "gcp_project")


@pytest.fixture
def credentials(monkeypatch):
    return monkeypatch.setenv("credentials", "{'secret': 'value'}")


def test__validate_env_variables_missing_dataset_schema_directory(
    gcp_project, credentials
):
    with pytest.raises(MissingConfigError) as exec_info:
        deploy._validate_env_variables()
    assert exec_info.value.args[0] == "Missing `dataset_schema_directory` config"


def test__validate_env_variables_missing_gcp_project(
    dataset_schema_directory, credentials
):
    with pytest.raises(MissingConfigError) as exec_info:
        deploy._validate_env_variables()
    assert exec_info.value.args[0] == "Missing `gcp_project` config"


def test__validate_env_variables_missing_credentials(
    gcp_project, dataset_schema_directory
):
    with pytest.raises(MissingConfigError) as exec_info:
        deploy._validate_env_variables()
    assert exec_info.value.args[0] == "Missing `credentials` config"


def test__validate_env_variables_all_variables_present(
    gcp_project, dataset_schema_directory, credentials
):
    deploy._validate_env_variables()
    assert True


def test__validate_if_path_exists_true(mocker, dataset_schema_directory):
    path_mock = mocker.patch("plugin_scripts.deploy.Path")
    path_mock.return_value.is_dir.return_value = True
    assert deploy._validate_if_path_exists()


def test__validate_if_path_exists_false(mocker, dataset_schema_directory):
    path_mock = mocker.patch("plugin_scripts.deploy.Path")
    path_mock.return_value.is_dir.return_value = False
    assert not deploy._validate_if_path_exists()


def test_main_schema_directory_false(
    mocker, gcp_project, dataset_schema_directory, credentials
):
    path_mock = mocker.patch("plugin_scripts.deploy.Path")
    path_mock.return_value.is_dir.return_value = False

    with pytest.raises(DatasetSchemaDirectoryNonExistent):
        deploy.main()


def test_main_false(mocker, gcp_project, dataset_schema_directory, credentials):
    path_mock = mocker.patch("plugin_scripts.deploy.Path")
    path_mock.return_value.is_dir.return_value = True
    mocker.patch("plugin_scripts.deploy.os.walk", return_value=[])
    mocker.patch("plugin_scripts.deploy.BigQuery")

    # Since no files to deploy, it should succeed
    deploy.main()


def test_main_true(mocker, gcp_project, dataset_schema_directory, credentials):
    path_mock = mocker.patch("plugin_scripts.deploy.Path")
    path_mock.return_value.is_dir.return_value = True
    mocker.patch("plugin_scripts.deploy.os.walk", return_value=[])
    mocker.patch("plugin_scripts.deploy.BigQuery")

    deploy.main()
    assert True
