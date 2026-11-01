"""Аудитований CSV-експортер: композиція замість успадкування. Помічник приходить через конструктор."""
from app.reporting.core_exporter import ExporterCore
from app.reporting.file_writer import LineFileWriter


class AuditedCsvExporter:
    def __init__(self, writer: LineFileWriter):
        self._writer = writer
        self.trail = []
        self.masked = set()

    def normalize(self, value, strict=False):
        return self.mask_field(self._writer.normalize(value, strict))

    def format_row(self, row):
        self.validate_row(row)
        line = self._writer.format_row(row, self.normalize)
        self.audit_stamp("row")
        return line

    def header(self, columns):
        line = self._writer.header(columns)
        self.audit_stamp("header")
        return line

    def footer(self, count):
        return self._writer.footer(count) + f" checksum={self.checksum()}"

    def flush(self):
        self.audit_stamp("flush")
        return self._writer.flush()

    def reset(self):
        self._writer.reset()
        self.trail = []

    def audit_stamp(self, event):
        self.trail.append(event)

    def audit_trail(self):
        return list(self.trail)

    def mask_field(self, text):
        return "***" if text in self.masked else text

    def validate_row(self, row):
        columns = self._writer.columns()
        if columns and len(row) != len(columns):
            raise ValueError("row does not match header")

    def export_all(self, columns, rows):
        self._writer.open_target()
        self.header(columns)
        for row in rows:
            self.format_row(row)
        self._writer.close_target()
        return self._writer.snapshot()

    def summary(self):
        return f"{self._writer.row_count()} rows, {len(self.trail)} audit events"

    def checksum(self):
        return sum(len(line) for line in self._writer.snapshot()) % 997


def build_audited_exporter():
    return AuditedCsvExporter(LineFileWriter(ExporterCore(",")))
