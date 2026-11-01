"""Ядро форматування (колишній базовий клас). Тепер це звичайний об'єкт без успадкування."""


class ExporterCore:
    def __init__(self, delimiter=","):
        self.delimiter = delimiter
        self.rows_written = 0
        self.columns = []

    def normalize(self, value, strict=False):
        text = "" if value is None else str(value).strip()
        return text.upper() if strict else text

    def quote(self, text):
        return '"' + text.replace('"', '""') + '"' if self.delimiter in text else text

    def format_row(self, row, normalize=None):
        pick = normalize or (lambda value: self.normalize(value, False))
        self.rows_written += 1
        return self.delimiter.join(self.quote(pick(v)) for v in row)

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
