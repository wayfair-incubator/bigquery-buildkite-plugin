"""Per-file deployment results, as a log summary and a Buildkite annotation."""

import html
from dataclasses import dataclass

MAX_ERROR_LENGTH = 500


@dataclass
class DeployResult:
    """Outcome of deploying one file."""

    path: str
    kind: str  # "structure" for a JSON definition, "sql" for a SQL file
    target: str  # fully qualified structure name, or the SQL file name
    # apply: "deployed"; plan: "would-create", "would-update", "unchanged";
    # validate and SQL in plan mode: "valid"; any mode: "failed"
    status: str
    seconds: float
    error: str = ""
    detail: str = ""  # what a plan would change, or bytes a SQL dry run would scan


_LABELS = {
    "deployed": "✅ deployed",
    "would-create": "➕ would create",
    "would-update": "✏️ would update",
    "unchanged": "➖ unchanged",
    "valid": "✅ valid",
    "failed": "❌ failed",
}


def _short(error: str) -> str:
    error = " ".join(error.split())
    if len(error) > MAX_ERROR_LENGTH:
        return error[: MAX_ERROR_LENGTH - 3] + "..."
    return error


def summary_text(results: list[DeployResult]) -> str:
    """Plain-text summary for the build log."""
    failed = [r for r in results if r.status == "failed"]
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    if set(counts) <= {"deployed", "failed"}:
        lines = [f"{len(results) - len(failed)} deployed, {len(failed)} failed"]
    else:
        lines = [", ".join(f"{n} {status}" for status, n in sorted(counts.items()))]
        for result in results:
            if result.detail and result.status != "failed":
                lines.append(
                    f"  {result.status} {result.target}: {_short(result.detail)}"
                )
    for result in failed:
        lines.append(f"  FAILED {result.path}: {_short(result.error)}")
    return "\n".join(lines)


def _cell(value: str) -> str:
    # Escape HTML so error text or file names cannot inject markup into the
    # annotation, and escape the table separator
    return html.escape(value, quote=False).replace("|", "&#124;")


def annotation_markdown(
    results: list[DeployResult], gcp_project: str, mode: str = "apply"
) -> str:
    """Markdown for `buildkite-agent annotate`; every dynamic value is escaped."""
    failed = [r for r in results if r.status == "failed"]
    if mode == "apply":
        title = "BigQuery deployment"
        ok_headline = f"{len(results)} file(s) deployed"
        failed_headline = f"{len(failed)} of {len(results)} file(s) failed to deploy"
    elif mode == "plan":
        changes = [r for r in results if r.status.startswith("would-")]
        title = "BigQuery plan (nothing was changed)"
        ok_headline = (
            f"{len(changes)} change(s) planned, {len(results)} file(s) checked"
        )
        failed_headline = f"{len(failed)} of {len(results)} file(s) cannot be applied"
    else:
        title = "BigQuery validation (nothing was changed)"
        ok_headline = f"{len(results)} file(s) valid"
        failed_headline = f"{len(failed)} of {len(results)} file(s) invalid"
    headline = failed_headline if failed else ok_headline
    lines = [
        f"#### {title} for `{_cell(gcp_project)}`: {headline}",
        "",
        "| File | Target | Result | Time | Details |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_cell(result.path)}`",
                    f"`{_cell(result.target)}`"
                    if result.kind == "structure"
                    else "SQL",
                    _LABELS.get(result.status, result.status),
                    f"{result.seconds:.1f}s",
                    _cell(_short(result.error or result.detail)),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"
