from plugin_scripts.report import DeployResult, annotation_markdown, summary_text


def _result(**overrides):
    values = {
        "path": "schemas/ds/orders.json",
        "kind": "structure",
        "target": "proj.ds.orders",
        "status": "deployed",
        "seconds": 1.234,
        "error": "",
    }
    values.update(overrides)
    return DeployResult(**values)


def test_summary_text_counts_and_lists_failures():
    results = [
        _result(),
        _result(path="schemas/ds/bad.json", status="failed", error="boom\nline two"),
    ]

    text = summary_text(results)

    assert text.splitlines()[0] == "1 deployed, 1 failed"
    assert "FAILED schemas/ds/bad.json: boom line two" in text


def test_annotation_has_a_row_per_file():
    markdown = annotation_markdown(
        [_result(), _result(path="q/run.sql", kind="sql", target="run")], "proj"
    )

    assert "2 file(s) deployed" in markdown
    assert (
        "| `schemas/ds/orders.json` | `proj.ds.orders` | ✅ deployed | 1.2s |  |"
        in markdown
    )
    assert "| `q/run.sql` | SQL |" in markdown


def test_annotation_reports_failures():
    markdown = annotation_markdown(
        [_result(status="failed", error="InvalidDefinitionException: nope")], "proj"
    )

    assert "1 of 1 file(s) failed to deploy" in markdown
    assert "❌ failed" in markdown
    assert "InvalidDefinitionException: nope" in markdown


def test_annotation_escapes_html_and_table_separators():
    markdown = annotation_markdown(
        [
            _result(
                path="schemas/ds/<script>.json",
                status="failed",
                error="<img src=x onerror=alert(1)> | injected",
            )
        ],
        "proj",
    )

    assert "<script>" not in markdown
    assert "<img" not in markdown
    assert "&lt;img" in markdown
    assert "| injected" not in markdown


def test_long_errors_are_truncated():
    markdown = annotation_markdown([_result(status="failed", error="x" * 5000)], "p")

    assert "x" * 600 not in markdown
    assert "..." in markdown


def test_plan_annotation_shows_planned_changes():
    results = [
        _result(status="would-update", detail="removes label team; adds column x"),
        _result(path="ds/new.json", target="proj.ds.new", status="would-create"),
        _result(path="ds/same.json", target="proj.ds.same", status="unchanged"),
    ]

    markdown = annotation_markdown(results, "proj", mode="plan")

    assert "BigQuery plan (nothing was changed)" in markdown
    assert "2 change(s) planned, 3 file(s) checked" in markdown
    assert "✏️ would update" in markdown
    assert "➕ would create" in markdown
    assert "removes label team; adds column x" in markdown


def test_plan_annotation_with_a_blocked_file():
    markdown = annotation_markdown(
        [_result(status="failed", error="Cannot change the partitioning")],
        "proj",
        mode="plan",
    )

    assert "1 of 1 file(s) cannot be applied" in markdown


def test_validate_annotation():
    markdown = annotation_markdown([_result(status="valid")], "proj", mode="validate")

    assert "BigQuery validation (nothing was changed)" in markdown
    assert "1 file(s) valid" in markdown


def test_plan_summary_counts_statuses_and_lists_details():
    text = summary_text(
        [
            _result(status="would-update", detail="removes the description"),
            _result(path="b.json", target="proj.ds.b", status="unchanged"),
        ]
    )

    assert text.splitlines()[0] == "1 unchanged, 1 would-update"
    assert "would-update proj.ds.orders: removes the description" in text
