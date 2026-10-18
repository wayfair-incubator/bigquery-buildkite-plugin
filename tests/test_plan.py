"""
Plan and validate modes, run against the real gbq with a fake Google client.

The fake client refuses every write, so these tests also prove that plan mode never
sends one, and they fail if a gbq upgrade starts writing through other client methods.
"""

import json

import pytest
from gbq import BigQuery
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from plugin_scripts import deploy
from plugin_scripts.deploy import _deploy_from_directory, _parse_patterns
from plugin_scripts.pipeline_exceptions import PlanViolation
from plugin_scripts.plan import PlanRecorder


class FakeClient:
    """Serves existing resources, and fails the test on any write."""

    def __init__(self, tables=None, routines=None, bytes_processed=1234):
        self.tables = tables or {}
        self.routines = routines or {}
        self.bytes_processed = bytes_processed
        self.queries = []

    def get_table(self, name):
        if name not in self.tables:
            raise NotFound(name)
        return self.tables[name]

    def get_routine(self, name):
        if name not in self.routines:
            raise NotFound(name)
        return self.routines[name]

    def query(self, query, job_config=None, project=None):
        self.queries.append((query, job_config))
        client = self

        class Job:
            total_bytes_processed = client.bytes_processed

            def result(self):
                return []

        return Job()

    def _write(self, *args, **kwargs):  # pragma: no cover - only on failure
        raise AssertionError("plan mode sent a write to BigQuery")

    create_table = update_table = create_routine = update_routine = _write
    delete_table = delete_routine = insert_rows = _write


def _table(name="proj.ds.t", schema=None, **properties):
    table = bigquery.Table(
        name, schema=schema or [bigquery.SchemaField("id", "INTEGER")]
    )
    for key, value in properties.items():
        setattr(table, key, value)
    return table


def _plan(tmp_path, definitions, client, include=None):
    """Plan every definition ({'ds/t.json': dict | 'text'}) and return the results."""
    for relative, definition in definitions.items():
        path = tmp_path / "schemas" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            definition if isinstance(definition, str) else json.dumps(definition)
        )
    bq = object.__new__(BigQuery)
    recorder = PlanRecorder(client)
    bq.bq_client = recorder
    results = []
    failed = _deploy_from_directory(
        bq=bq,
        gcp_project="proj",
        dataset_schema_directory=str(tmp_path / "schemas"),
        updated_files=[],
        execute_only_changed_files=False,
        fail_pipeline_on_first_exception=False,
        results=results,
        include=_parse_patterns(include),
        mode="plan",
        recorder=recorder,
    )
    return failed, {r.target: r for r in results}


SCHEMA = [{"name": "id", "type": "INTEGER"}]


def test_missing_table_would_be_created(tmp_path):
    failed, results = _plan(tmp_path, {"ds/t.json": {"schema": SCHEMA}}, FakeClient())

    assert not failed
    assert results["proj.ds.t"].status == "would-create"


def test_identical_table_is_unchanged(tmp_path):
    client = FakeClient(tables={"proj.ds.t": _table()})

    failed, results = _plan(tmp_path, {"ds/t.json": {"schema": SCHEMA}}, client)

    assert not failed
    assert results["proj.ds.t"].status == "unchanged"


def test_omitted_labels_description_and_clustering_are_reported_as_removals(tmp_path):
    existing = _table(
        labels={"team": "abc"}, description="old", clustering_fields=["id"]
    )
    client = FakeClient(tables={"proj.ds.t": existing})

    _failed, results = _plan(tmp_path, {"ds/t.json": {"schema": SCHEMA}}, client)

    result = results["proj.ds.t"]
    assert result.status == "would-update"
    assert "removes label team" in result.detail
    assert "removes the description" in result.detail
    assert "clustering id -> none" in result.detail


def test_new_column_is_reported(tmp_path):
    client = FakeClient(tables={"proj.ds.t": _table()})
    definition = {"schema": [*SCHEMA, {"name": "name", "type": "STRING"}]}

    _failed, results = _plan(tmp_path, {"ds/t.json": definition}, client)

    assert results["proj.ds.t"].status == "would-update"
    assert "adds column name" in results["proj.ds.t"].detail


def test_view_query_change_is_reported(tmp_path):
    view = bigquery.Table("proj.ds.v")
    view.view_query = "SELECT 1"
    client = FakeClient(tables={"proj.ds.v": view})

    _failed, results = _plan(
        tmp_path, {"ds/v.json": {"view_query": "SELECT 2"}}, client
    )

    assert results["proj.ds.v"].status == "would-update"
    assert "view query" in results["proj.ds.v"].detail


def test_partitioning_change_is_blocked_like_apply_would_be(tmp_path):
    client = FakeClient(tables={"proj.ds.t": _table()})  # not partitioned
    definition = {
        "schema": SCHEMA,
        "partition": {"type": "time", "definition": {"type": "DAY"}},
    }

    failed, results = _plan(tmp_path, {"ds/t.json": definition}, client)

    assert failed
    assert results["proj.ds.t"].status == "failed"
    assert "Cannot change the partitioning" in results["proj.ds.t"].error


def test_invalid_definition_fails(tmp_path):
    failed, results = _plan(
        tmp_path, {"ds/t.json": {"partition": "nonsense"}}, FakeClient()
    )

    assert failed
    assert results["proj.ds.t"].status == "failed"


def _procedure(body="SELECT 1"):
    return {"type": "stored_procedure", "body": body, "arguments": []}


def _existing_routine(body="SELECT 1"):
    return bigquery.Routine("proj.ds.p", type_="PROCEDURE", language="SQL", body=body)


def test_routine_states(tmp_path):
    client = FakeClient(routines={"proj.ds.p": _existing_routine()})

    _failed, same = _plan(tmp_path, {"ds/p.json": _procedure()}, client)
    _failed, changed = _plan(tmp_path, {"ds/p.json": _procedure("SELECT 2")}, client)
    _failed, new = _plan(tmp_path, {"ds/p.json": _procedure()}, FakeClient())

    assert same["proj.ds.p"].status == "unchanged"
    assert changed["proj.ds.p"].status == "would-update"
    assert "body" in changed["proj.ds.p"].detail
    assert new["proj.ds.p"].status == "would-create"


def test_sql_is_dry_run_and_never_executed(tmp_path):
    client = FakeClient()

    failed, results = _plan(tmp_path, {"ds/run.sql": "DELETE FROM t WHERE 1=1"}, client)

    assert not failed
    assert results["run"].status == "valid"
    assert "1234 bytes" in results["run"].detail
    assert len(client.queries) == 1
    assert client.queries[0][1].dry_run is True


def test_plan_recorder_refuses_other_changes_and_real_queries():
    recorder = PlanRecorder(FakeClient())

    with pytest.raises(PlanViolation):
        recorder.delete_dataset("proj.ds")
    with pytest.raises(PlanViolation):
        recorder.query("DELETE FROM t")
    with pytest.raises(PlanViolation):
        recorder.query("DELETE FROM t", job_config=bigquery.QueryJobConfig())


# validate mode


def _validate(tmp_path, files, include=None):
    for relative, text in files.items():
        path = tmp_path / "schemas" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if isinstance(text, str) else json.dumps(text))
    results = []
    failed = _deploy_from_directory(
        bq=None,
        gcp_project="proj",
        dataset_schema_directory=str(tmp_path / "schemas"),
        updated_files=[],
        execute_only_changed_files=False,
        fail_pipeline_on_first_exception=False,
        results=results,
        mode="validate",
    )
    return failed, {r.path.split("/")[-1]: r for r in results}


def test_validate_accepts_valid_definitions_without_a_client(tmp_path):
    failed, results = _validate(
        tmp_path,
        {
            "ds/t.json": {"schema": SCHEMA, "labels": {"a": "b"}},
            "ds/v.json": {"view_query": "SELECT 1"},
            "ds/p.json": _procedure(),
            "ds/q.sql": "SELECT 1",
        },
    )

    assert not failed
    assert {r.status for r in results.values()} == {"valid"}


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("bad.json", "{not json"),
        ("bad.json", {"partition": "nonsense"}),
        ("bad.json", [1, 2, 3]),
        ("empty.sql", "  \n"),
    ],
)
def test_validate_reports_invalid_files(tmp_path, name, content):
    failed, results = _validate(tmp_path, {f"ds/{name}": content})

    assert failed
    assert results[name].status == "failed"


def test_validate_mode_needs_no_credentials_or_bigquery(tmp_path, monkeypatch, mocker):
    schemas = tmp_path / "schemas" / "ds"
    schemas.mkdir(parents=True)
    (schemas / "t.json").write_text(json.dumps({"schema": SCHEMA}))
    monkeypatch.setenv("gcp_project", "proj")
    monkeypatch.setenv("dataset_schema_directory", str(tmp_path / "schemas"))
    monkeypatch.setenv("mode", "validate")
    bigquery_cls = mocker.patch("plugin_scripts.deploy.BigQuery")
    bigquery_cls._get_structure = BigQuery._get_structure
    bigquery_cls._handle_routine_arguments = BigQuery._handle_routine_arguments

    deploy._deploy()

    bigquery_cls.assert_not_called()


def test_invalid_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("gcp_project", "proj")
    monkeypatch.setenv("dataset_schema_directory", "schemas")
    monkeypatch.setenv("mode", "destroy")

    with pytest.raises(deploy.MissingConfigError):
        deploy._validate_env_variables()
