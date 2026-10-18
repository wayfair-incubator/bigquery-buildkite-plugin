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
    status: str  # "deployed" or "failed"
    seconds: float
    error: str = ""


def _short(error: str) -> str:
    error = " ".join(error.split())
    if len(error) > MAX_ERROR_LENGTH:
        return error[: MAX_ERROR_LENGTH - 3] + "..."
    return error


def summary_text(results: list[DeployResult]) -> str:
    """Plain-text summary for the build log."""
    failed = [r for r in results if r.status == "failed"]
    lines = [f"{len(results) - len(failed)} deployed, {len(failed)} failed"]
    for result in failed:
        lines.append(f"  FAILED {result.path}: {_short(result.error)}")
    return "\n".join(lines)


def _cell(value: str) -> str:
    # Escape HTML so error text or file names cannot inject markup into the
    # annotation, and escape the table separator
    return html.escape(value, quote=False).replace("|", "&#124;")


def annotation_markdown(results: list[DeployResult], gcp_project: str) -> str:
    """Markdown for `buildkite-agent annotate`; every dynamic value is escaped."""
    failed = [r for r in results if r.status == "failed"]
    if failed:
        headline = f"{len(failed)} of {len(results)} file(s) failed to deploy"
    else:
        headline = f"{len(results)} file(s) deployed"
    lines = [
        f"#### BigQuery deployment to `{_cell(gcp_project)}`: {headline}",
        "",
        "| File | Target | Result | Time | Error |",
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
                    "✅ deployed" if result.status == "deployed" else "❌ failed",
                    f"{result.seconds:.1f}s",
                    _cell(_short(result.error)),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"
