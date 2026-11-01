import pytest

from app.reporting.audit_exporter import AuditedCsvExporter, build_audited_exporter
from app.reporting.core_exporter import ExporterCore
from app.reporting.file_writer import LineFileWriter

ROWS = [["Ann", " 10 "], ["Bob", None]]


def test_core_quotes_and_counts_rows():
    core = ExporterCore(",")
    assert core.format_row(["a,b", " c "]) == '"a,b",c'
    assert core.row_count() == 1


def test_core_header_and_footer():
    core = ExporterCore(";")
    assert core.header(["id", "name"]) == "id;name"
    assert core.footer(2) == "# rows: 2"


def test_writer_writes_lines_through_core():
    writer = LineFileWriter(ExporterCore(";"))
    writer.open_target()
    writer.header(["id", "name"])
    assert writer.format_row(["1", "x\ty"]) == "1;x y"
    assert writer.flush() == 2


def test_writer_requires_open_target():
    with pytest.raises(ValueError):
        LineFileWriter(ExporterCore(";")).format_row(["1"])


def test_audited_export_all_produces_lines():
    exporter = build_audited_exporter()
    assert exporter.export_all(["name", "qty"], ROWS) == ["name,qty", "Ann,10", "Bob,"]


def test_audited_masks_secret_fields():
    exporter = build_audited_exporter()
    exporter.masked.add("Ann")
    assert exporter.export_all(["name", "qty"], ROWS)[1] == "***,10"


def test_audited_trail_records_events():
    exporter = build_audited_exporter()
    exporter.export_all(["name", "qty"], ROWS)
    assert exporter.audit_trail() == ["header", "row", "row"]


def test_audited_rejects_wrong_column_count():
    exporter = build_audited_exporter()
    exporter._writer.open_target()
    exporter.header(["name", "qty"])
    with pytest.raises(ValueError):
        exporter.format_row(["only-one"])


def test_audited_footer_contains_checksum():
    exporter = build_audited_exporter()
    exporter.export_all(["name", "qty"], ROWS)
    assert exporter.footer(2).startswith("# rows: 2 checksum=")


def test_exporter_accepts_injected_writer():
    exporter = AuditedCsvExporter(LineFileWriter(ExporterCore(";")))
    assert exporter.export_all(["a", "b"], [["1", "2"]]) == ["a;b", "1;2"]
