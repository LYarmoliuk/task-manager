"""Запис рядків у «файл» (колишній клас-нащадок). Ядро передається через конструктор."""
from app.reporting.core_exporter import ExporterCore


class LineFileWriter:
    def __init__(self, core: ExporterCore):
        self._core = core
        self._lines = []
        self._is_open = False

    def normalize(self, value, strict=False):
        return self._core.normalize(value, strict).replace("\t", " ")

    def format_row(self, row, normalize=None):
        line = self._core.format_row(row, normalize or self.normalize)
        self.write_line(line)
        return line

    def header(self, columns):
        line = self._core.header(columns)
        self.write_line(line)
        return line

    def footer(self, count):
        return self._core.footer(count)

    def row_count(self):
        return self._core.row_count()

    def reset(self):
        self._core.reset()
        self._lines = []

    def open_target(self):
        self._is_open = True
        self._lines = []

    def write_line(self, text):
        if not self._is_open:
            raise ValueError("target is closed")
        self._lines.append(self.encode(text))

    def close_target(self):
        self._is_open = False

    def flush(self):
        return len(self._lines)

    def set_delimiter(self, char):
        self._core.delimiter = char

    def encode(self, text):
        return text.strip()

    def columns(self):
        return self._core.columns

    def snapshot(self):
        return list(self._lines)
