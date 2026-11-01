import pytest

from app.reporting.audit_exporter import AuditedCsvExporter
from app.reporting.base_exporter import BaseExporter
from app.reporting.file_exporter import FileExporter

ROWS = [["Ann", " 10 "], ["Bob", None]]


def test_base_quotes_and_counts_rows():
    exporter = BaseExporter(",")
    assert exporter.format_row(["a,b", " c "]) == '"a,b",c'
    assert exporter.row_count() == 1


def test_base_header_and_footer():
    exporter = BaseExporter(";")
    assert exporter.header(["id", "name"]) == "id;name"
    assert exporter.footer(2) == "# rows: 2"


def test_file_exporter_writes_lines():
    exporter = FileExporter()
    exporter.open_target()
    exporter.header(["id", "name"])
    assert exporter.format_row(["1", "x\ty"]) == "1;x y"
    assert exporter.flush() == 2


def test_file_exporter_requires_open_target():
    with pytest.raises(ValueError):
        FileExporter().format_row(["1"])


def test_audited_export_all_produces_lines():
    exporter = AuditedCsvExporter()
    assert exporter.export_all(["name", "qty"], ROWS) == ["name,qty", "Ann,10", "Bob,"]


def test_audited_masks_secret_fields():
    exporter = AuditedCsvExporter()
    exporter.masked.add("Ann")
    assert exporter.export_all(["name", "qty"], ROWS)[1] == "***,10"


def test_audited_trail_records_events():
    exporter = AuditedCsvExporter()
    exporter.export_all(["name", "qty"], ROWS)
    assert exporter.audit_trail() == ["header", "row", "row"]


def test_audited_rejects_wrong_column_count():
    exporter = AuditedCsvExporter()
    exporter.open_target()
    exporter.header(["name", "qty"])
    with pytest.raises(ValueError):
        exporter.format_row(["only-one"])


def test_audited_footer_contains_checksum():
    exporter = AuditedCsvExporter()
    exporter.export_all(["name", "qty"], ROWS)
    assert exporter.footer(2).startswith("# rows: 2 checksum=")
