"""Integration tests for deploy module with real file I/O."""

import json
import tempfile
from pathlib import Path

import pytest

from plugin_scripts.deploy import _deploy_from_directory


@pytest.fixture
def temp_schema_dir():
    """Create temporary directory with test schema files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory structure: tmpdir/schemas/test_dataset/
        schemas_root = Path(tmpdir) / "schemas"
        dataset_dir = schemas_root / "test_dataset"
        dataset_dir.mkdir(parents=True)

        # Create test JSON schema file
        table_schema = {
            "schema": [
                {"name": "id", "type": "INTEGER", "mode": "REQUIRED"},
                {"name": "name", "type": "STRING", "mode": "NULLABLE"},
                {"name": "created_at", "type": "TIMESTAMP", "mode": "REQUIRED"},
            ]
        }
        (dataset_dir / "test_table.json").write_text(json.dumps(table_schema, indent=2))

        # Create test SQL file
        sql_query = """
-- Test SQL query
SELECT
    id,
    name,
    created_at
FROM
    `test_project.test_dataset.test_table`
WHERE
    created_at > CURRENT_TIMESTAMP()
LIMIT 100;
"""
        (dataset_dir / "test_query.sql").write_text(sql_query)

        # Create a nested subdirectory with another schema
        nested_dir = dataset_dir / "nested"
        nested_dir.mkdir()
        (nested_dir / "nested_table.json").write_text(
            json.dumps({"schema": [{"name": "value", "type": "STRING"}]})
        )

        # Create a file that should be skipped
        (dataset_dir / "README.md").write_text("# Test Dataset")

        yield str(schemas_root)


def test_deploy_from_directory_with_real_files(temp_schema_dir, mocker):
    """Test deployment with actual file I/O."""
    mock_bq = mocker.Mock()

    result = _deploy_from_directory(
        bq=mock_bq,
        gcp_project="test-project",
        dataset_schema_directory=temp_schema_dir,
        updated_files=[],
        execute_only_changed_files=False,
        fail_pipeline_on_first_exception=False,
    )

    # Should not fail
    assert not result

    # Verify BigQuery methods were called
    assert mock_bq.create_or_update_structure.called
    assert mock_bq.execute.called

    # Verify correct number of calls
    # 2 JSON files (test_table.json, nested_table.json)
    assert mock_bq.create_or_update_structure.call_count == 2
    # 1 SQL file (test_query.sql)
    assert mock_bq.execute.call_count == 1


def test_deploy_from_directory_with_filtered_files(temp_schema_dir, mocker):
    """Test deployment with file filtering based on changed files."""
    mock_bq = mocker.Mock()

    # Only include one specific file
    changed_file = str(Path(temp_schema_dir) / "test_dataset" / "test_table.json")

    result = _deploy_from_directory(
        bq=mock_bq,
        gcp_project="test-project",
        dataset_schema_directory=temp_schema_dir,
        updated_files=[changed_file],
        execute_only_changed_files=True,
        fail_pipeline_on_first_exception=False,
    )

    assert not result

    # Only the filtered file should be processed
    assert mock_bq.create_or_update_structure.call_count == 1
    assert mock_bq.execute.call_count == 0


def test_deploy_from_directory_skips_non_schema_files(temp_schema_dir, mocker):
    """Test that non-schema files (like README.md) are skipped."""
    mock_bq = mocker.Mock()

    result = _deploy_from_directory(
        bq=mock_bq,
        gcp_project="test-project",
        dataset_schema_directory=temp_schema_dir,
        updated_files=[],
        execute_only_changed_files=False,
        fail_pipeline_on_first_exception=False,
    )

    assert not result

    # Verify README.md was not processed (no extra calls)
    total_calls = (
        mock_bq.create_or_update_structure.call_count + mock_bq.execute.call_count
    )
    assert total_calls == 3  # Only 2 JSON + 1 SQL


def test_deploy_from_directory_handles_invalid_json(temp_schema_dir, mocker):
    """Test handling of invalid JSON files."""
    mock_bq = mocker.Mock()

    # Create invalid JSON file
    dataset_dir = Path(temp_schema_dir) / "test_dataset"
    (dataset_dir / "invalid.json").write_text("{invalid json content")

    result = _deploy_from_directory(
        bq=mock_bq,
        gcp_project="test-project",
        dataset_schema_directory=temp_schema_dir,
        updated_files=[],
        execute_only_changed_files=False,
        fail_pipeline_on_first_exception=False,
    )

    # Should fail due to invalid JSON
    assert result is True


def test_deploy_from_directory_fails_fast(temp_schema_dir, mocker):
    """Test that deployment fails fast when configured."""
    mock_bq = mocker.Mock()
    # Make the BigQuery call fail
    mock_bq.create_or_update_structure.side_effect = Exception("BigQuery error")

    result = _deploy_from_directory(
        bq=mock_bq,
        gcp_project="test-project",
        dataset_schema_directory=temp_schema_dir,
        updated_files=[],
        execute_only_changed_files=False,
        fail_pipeline_on_first_exception=True,
    )

    # Should fail
    assert result is True

    # Should stop after first failure
    assert mock_bq.create_or_update_structure.call_count == 1


def test_deploy_from_directory_continues_on_error(temp_schema_dir, mocker):
    """Test that deployment continues on error when configured."""
    mock_bq = mocker.Mock()
    # Make the BigQuery call fail
    mock_bq.create_or_update_structure.side_effect = Exception("BigQuery error")

    result = _deploy_from_directory(
        bq=mock_bq,
        gcp_project="test-project",
        dataset_schema_directory=temp_schema_dir,
        updated_files=[],
        execute_only_changed_files=False,
        fail_pipeline_on_first_exception=False,
    )

    # Should fail but continue
    assert result is True

    # Should attempt all files
    # 2 JSON files should be attempted
    assert mock_bq.create_or_update_structure.call_count == 2


def test_deploy_verifies_correct_parameters(temp_schema_dir, mocker):
    """Test that correct parameters are passed to BigQuery methods."""
    mock_bq = mocker.Mock()

    _deploy_from_directory(
        bq=mock_bq,
        gcp_project="my-gcp-project",
        dataset_schema_directory=temp_schema_dir,
        updated_files=[],
        execute_only_changed_files=False,
        fail_pipeline_on_first_exception=False,
    )

    # Verify create_or_update_structure was called with correct parameters
    calls = mock_bq.create_or_update_structure.call_args_list
    for call in calls:
        assert call.kwargs["project"] == "my-gcp-project"
        assert call.kwargs["dataset"] in ("test_dataset", "nested")
        assert call.kwargs["structure_id"] in ("test_table", "nested_table")
        assert "json_schema" in call.kwargs

    # Verify execute was called with SQL query
    sql_call = mock_bq.execute.call_args
    assert "query" in sql_call.kwargs
    assert "SELECT" in sql_call.kwargs["query"]
