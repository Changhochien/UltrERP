"""
SQL dump parser - extracts table data from INSERT statements.
"""
import re
from dataclasses import dataclass
from typing import Iterator, List


@dataclass
class TableData:
    table_name: str
    columns: List[str]
    rows: List[List[str]]


# Pre-compiled regex for INSERT detection
INSERT_PATTERN = re.compile(
    r"INSERT INTO (\w+)\s*(?:\(([^)]+)\))?\s*VALUES\s*(.+?);",
    re.DOTALL | re.IGNORECASE,
)


class SQLDumpParser:
    """
    Parse PostgreSQL dump and extract table data.
    """

    def parse_file(self, filepath: str, encoding: str = "utf-8") -> Iterator[TableData]:
        """
        Parse SQL dump file and yield table data.
        Uses streaming to handle large files.
        """
        table_data = {}

        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        for match in INSERT_PATTERN.finditer(content):
            table_name = match.group(1)
            cols_str = match.group(2)
            values_str = match.group(3)

            columns = []
            if cols_str:
                columns = [c.strip() for c in cols_str.split(",")]

            rows = list(self._parse_values(values_str))

            if table_name not in table_data:
                table_data[table_name] = {"columns": columns, "rows": []}
                if columns:
                    table_data[table_name]["columns"] = columns

            table_data[table_name]["rows"].extend(rows)

        for table_name, data in table_data.items():
            yield TableData(
                table_name=table_name,
                columns=data["columns"],
                rows=data["rows"],
            )

    def _parse_values(self, values_str: str) -> Iterator[List[str]]:
        """
        Parse VALUES clause into rows.
        Yields each row as a list of values.
        """
        rows = []
        depth = 0
        current_row = []
        current_value = ""
        in_string = False
        string_char = None
        i = 0

        while i < len(values_str):
            char = values_str[i]
            prev_char = values_str[i - 1] if i > 0 else ""

            # String handling - check for escaped quotes
            if char in ("'", '"'):
                # Count preceding backslashes
                num_escapes = 0
                j = i - 1
                while j >= 0 and values_str[j] == "\\":
                    num_escapes += 1
                    j -= 1

                # Quote is escaped only if odd number of backslashes
                if num_escapes % 2 == 0:
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None

            # Paren tracking (only outside strings)
            if not in_string:
                if char == "(" and depth == 0:
                    current_row = []
                    current_value = ""
                    depth = 1
                    i += 1
                    continue
                elif char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                    if depth == 0:
                        current_row.append(current_value.strip())
                        yield current_row
                        current_value = ""
                        # Skip optional comma
                        while i + 1 < len(values_str) and values_str[i + 1] in " \t\n":
                            i += 1
                        if i + 1 < len(values_str) and values_str[i + 1] == ",":
                            i += 1
                        i += 1
                        continue

            if depth > 0:
                current_value += char

            i += 1
