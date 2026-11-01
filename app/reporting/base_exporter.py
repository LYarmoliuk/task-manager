"""Рівень 1 ієрархії експортерів: базовий клас."""


class BaseExporter:
    def __init__(self, delimiter=","):
        self.delimiter = delimiter
        self.rows_written = 0
        self.columns = []

    def normalize(self, value, strict):
        text = "" if value is None else str(value).strip()
        return text.upper() if strict else text

    def quote(self, text):
        return '"' + text.replace('"', '""') + '"' if self.delimiter in text else text

    def format_row(self, row):
        self.rows_written += 1
        return self.delimiter.join(self.quote(self.normalize(v, False)) for v in row)

    def header(self, columns):
        self.columns = list(columns)
        return self.delimiter.join(self.columns)

    def footer(self, count):
        return f"# rows: {count}"

    def row_count(self):
        return self.rows_written

    def reset(self):
        self.rows_written = 0
        self.columns = []

    def describe(self):
        return f"{type(self).__name__}(delimiter={self.delimiter!r})"
