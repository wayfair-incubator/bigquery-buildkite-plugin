"""
Read-only "plan" support.

gbq reads an existing table or routine, works out what differs and writes the change
in one call. To show what *would* change without changing anything, `PlanRecorder`
wraps the BigQuery client that gbq uses: reads go to BigQuery, the four write calls
gbq makes for structures are recorded instead of sent, and every other call that
could change something is refused. gbq therefore runs exactly the code it runs when
applying, including its checks (for example it still rejects a partitioning change).
"""

import copy
from dataclasses import dataclass, field
from typing import Any

from plugin_scripts.pipeline_exceptions import PlanViolation

# Client methods whose name starts like this change something and are refused
_MUTATING_PREFIXES = (
    "create_",
    "update_",
    "delete_",
    "insert_",
    "load_",
    "copy_",
    "extract_",
    "set_",
    "undelete_",
)


@dataclass
class PlannedChange:
    target: str
    action: str  # "create", "update" or "unchanged"
    details: list[str] = field(default_factory=list)


def _table_name(table: Any) -> str:
    return f"{table.project}.{table.dataset_id}.{table.table_id}"


def _routine_name(routine: Any) -> str:
    return f"{routine.project}.{routine.dataset_id}.{routine.routine_id}"


def _describe_label_changes(old: dict, new: dict) -> list[str]:
    details = []
    for key, value in new.items():
        if value is None:
            details.append(f"removes label {key}")
        elif key not in old:
            details.append(f"adds label {key}")
        elif old[key] != value:
            details.append(f"changes label {key}")
    return details


def _describe_schema_changes(old: list, new: list) -> list[str]:
    old_by_name = {f.name: f.to_api_repr() for f in old}
    new_by_name = {f.name: f.to_api_repr() for f in new}
    details = []
    for name in new_by_name.keys() - old_by_name.keys():
        details.append(f"adds column {name}")
    for name in old_by_name.keys() - new_by_name.keys():
        details.append(f"removes column {name}")
    for name in new_by_name.keys() & old_by_name.keys():
        if new_by_name[name] != old_by_name[name]:
            details.append(f"changes column {name}")
    return sorted(details) or ["changes schema"]


def describe_table_update(old: Any, new: Any, fields: list[str]) -> list[str]:
    """Human-readable description of the fields gbq sends in an update_table call."""
    details: list[str] = []
    for name in fields:
        if name == "labels":
            details += _describe_label_changes(old.labels or {}, new.labels or {})
        elif name == "description":
            if not new.description:
                details.append("removes the description")
            elif not old.description:
                details.append("sets the description")
            else:
                details.append("changes the description")
        elif name == "clustering_fields":
            old_clustering = ", ".join(old.clustering_fields or []) or "none"
            new_clustering = ", ".join(new.clustering_fields or []) or "none"
            details.append(f"clustering {old_clustering} -> {new_clustering}")
        elif name == "schema":
            details += _describe_schema_changes(list(old.schema), list(new.schema))
        elif name == "view_query":
            details.append("changes the view query")
        elif name == "time_partitioning":
            before = (
                old.time_partitioning.expiration_ms if old.time_partitioning else None
            )
            after = (
                new.time_partitioning.expiration_ms if new.time_partitioning else None
            )
            details.append(f"partition expiration {before} -> {after} ms")
        else:
            details.append(f"changes {name}")
    return details


def describe_routine_update(old: Any, new: Any) -> list[str]:
    """What differs between an existing routine and the one gbq would write."""
    details = []
    if old.body != new.body:
        details.append("changes the body")
    old_args = [a.to_api_repr() for a in old.arguments or []]
    new_args = [a.to_api_repr() for a in new.arguments or []]
    if old_args != new_args:
        details.append("changes the arguments")
    if (old.description or None) != (new.description or None):
        details.append("changes the description")
    return details


class PlanRecorder:
    """Stand-in for `google.cloud.bigquery.Client` that records instead of writing."""

    def __init__(self, client: Any):
        self._client = client
        self.changes: list[PlannedChange] = []
        self._tables: dict[str, Any] = {}
        self._routines: dict[str, Any] = {}

    # Reads: delegate, keeping a copy of what existed before gbq mutates it
    def get_table(self, table: Any, *args: Any, **kwargs: Any) -> Any:
        result = self._client.get_table(table, *args, **kwargs)
        self._tables[_table_name(result)] = copy.deepcopy(result)
        return result

    def get_routine(self, routine: Any, *args: Any, **kwargs: Any) -> Any:
        result = self._client.get_routine(routine, *args, **kwargs)
        self._routines[_routine_name(result)] = copy.deepcopy(result)
        return result

    # Writes gbq makes for structures: record
    def create_table(self, table: Any, *args: Any, **kwargs: Any) -> Any:
        self.changes.append(PlannedChange(_table_name(table), "create"))
        return table

    def update_table(self, table: Any, fields: list[str], *a: Any, **k: Any) -> Any:
        name = _table_name(table)
        before = self._tables.get(name)
        details = describe_table_update(before, table, fields) if before else []
        self.changes.append(PlannedChange(name, "update", details))
        return table

    def create_routine(self, routine: Any, *args: Any, **kwargs: Any) -> Any:
        self.changes.append(PlannedChange(_routine_name(routine), "create"))
        return routine

    def update_routine(self, routine: Any, fields: list[str], *a: Any, **k: Any) -> Any:
        name = _routine_name(routine)
        before = self._routines.get(name)
        details = describe_routine_update(before, routine) if before else []
        # gbq always sends the update; only an actual difference is a change
        action = "update" if details else "unchanged"
        self.changes.append(PlannedChange(name, action, details))
        return routine

    # Only dry runs may reach the query API
    def query(self, query: str, *args: Any, job_config: Any = None, **kwargs: Any):
        if job_config is None or not getattr(job_config, "dry_run", False):
            raise PlanViolation("Only dry-run queries are allowed in plan mode")
        return self._client.query(query, *args, job_config=job_config, **kwargs)

    def __getattr__(self, name: str) -> Any:
        if name.startswith(_MUTATING_PREFIXES):
            raise PlanViolation(f"{name} is not allowed in plan mode")
        return getattr(self._client, name)

    def change_since(self, index: int) -> PlannedChange:
        """The last change recorded after `index`; "unchanged" if gbq wrote nothing."""
        if len(self.changes) > index:
            return self.changes[-1]
        return PlannedChange("", "unchanged")
