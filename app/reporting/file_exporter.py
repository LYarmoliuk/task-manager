"""Рівень 2: експортер, що пише рядки у «файл» (список у пам'яті). Перевизначає частину логіки базового."""
from app.reporting.base_exporter import BaseExporter


class FileExporter(BaseExporter):
    def __init__(self, delimiter=";"):
        super().__init__(delimiter)
        self.lines = []
        self.is_open = False

    def normalize(self, value):
        return super().normalize(value).replace("\t", " ")

    def format_row(self, row):
        line = super().format_row(row)
        self.write_line(line)
        return line

    def header(self, columns):
        line = super().header(columns)
        self.write_line(line)
        return line

    def reset(self):
        super().reset()
        self.lines = []

    def open_target(self):
        self.is_open = True
        self.lines = []

    def write_line(self, text):
        if not self.is_open:
            raise ValueError("target is closed")
        self.lines.append(self.encode(text))

    def close_target(self):
        self.is_open = False

    def flush(self):
        return len(self.lines)

    def set_delimiter(self, char):
        self.delimiter = char

    def encode(self, text):
        return text.strip()
