"""Рівень 3: аудитований CSV-експортер. Перевизначає майже все, що отримав від предків."""
from app.reporting.file_exporter import FileExporter


class AuditedCsvExporter(FileExporter):
    def __init__(self):
        super().__init__(",")
        self.trail = []
        self.masked = set()

    def normalize(self, value):
        return self.mask_field(super().normalize(value))

    def format_row(self, row):
        self.validate_row(row)
        line = super().format_row(row)
        self.audit_stamp("row")
        return line

    def header(self, columns):
        line = super().header(columns)
        self.audit_stamp("header")
        return line

    def footer(self, count):
        return super().footer(count) + f" checksum={self.checksum()}"

    def flush(self):
        self.audit_stamp("flush")
        return super().flush()

    def reset(self):
        super().reset()
        self.trail = []

    def audit_stamp(self, event):
        self.trail.append(event)

    def audit_trail(self):
        return list(self.trail)

    def mask_field(self, text):
        return "***" if text in self.masked else text

    def validate_row(self, row):
        if self.columns and len(row) != len(self.columns):
            raise ValueError("row does not match header")

    def export_all(self, columns, rows):
        self.open_target()
        self.header(columns)
        for row in rows:
            self.format_row(row)
        self.close_target()
        return list(self.lines)

    def summary(self):
        return f"{self.row_count()} rows, {len(self.trail)} audit events"

    def checksum(self):
        return sum(len(line) for line in self.lines) % 997
