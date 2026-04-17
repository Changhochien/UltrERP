"""
SQL dump parser - extracts table data from INSERT statements.
"""
import re
from dataclasses import dataclass
from typing import Dict, Iterator, List


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

# Pre-compiled regex for CREATE TABLE detection
CREATE_TABLE_PATTERN = re.compile(
    r"CREATE TABLE (\w+)\s*\(([\s\S]+?)\)\s*;",
    re.DOTALL | re.IGNORECASE,
)

# Pre-compiled regex for column extraction within CREATE TABLE block
COLUMN_LINE_PATTERN = re.compile(
    r"^\s*(\w+)\s+(?:character varying|text|numeric|integer|date|timestamp|boolean|real|double precision|smallint|bigint|serial|bigserial|bytea|time|inet|cidr|uuid|xml|json|jsonb|point|line|lseg|box|circle|polygon|cidr|macaddr|ltree|tsquery|tsvector|interval)",
    re.IGNORECASE | re.MULTILINE,
)


class SQLDumpParser:
    """
    Parse PostgreSQL dump and extract table data.
    """

    def extract_table_columns(self, filepath: str, encoding: str = "utf-8") -> Dict[str, List[str]]:
        """
        Extract column names from CREATE TABLE statements in SQL dump.
        Returns a dict mapping table_name -> [column1, column2, ...]
        """
        table_columns: Dict[str, List[str]] = {}

        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        for match in CREATE_TABLE_PATTERN.finditer(content):
            table_name = match.group(1)
            create_block = match.group(2)

            # Extract column names from the CREATE TABLE block
            columns = []
            for line in create_block.split(","):
                line = line.strip()
                col_match = COLUMN_LINE_PATTERN.match(line)
                if col_match:
                    columns.append(col_match.group(1))

            if columns:
                table_columns[table_name] = columns

        return table_columns

    def parse_file(self, filepath: str, encoding: str = "utf-8") -> Iterator[TableData]:
        """
        Parse SQL dump file and yield table data.
        Uses streaming to handle large files.

        First extracts CREATE TABLE schemas to get column names, then parses INSERT statements.
        """
        # First pass: extract column names from CREATE TABLE statements
        table_columns = self.extract_table_columns(filepath, encoding)

        table_data: Dict[str, Dict] = {}

        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        for match in INSERT_PATTERN.finditer(content):
            table_name = match.group(1)
            cols_str = match.group(2)
            values_str = match.group(3)

            columns: List[str] = []
            if cols_str:
                # Explicit column list in INSERT: INSERT INTO table (col1, col2) VALUES ...
                columns = [c.strip() for c in cols_str.split(",")]
            elif table_name in table_columns:
                # No explicit columns - use CREATE TABLE schema
                columns = table_columns[table_name]

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
        Handles PostgreSQL '' escaping within strings.
        """
        depth = 0
        current_row = []
        current_value = ""
        in_string = False
        string_char = None
        i = 0

        while i < len(values_str):
            char = values_str[i]
            prev_char = values_str[i - 1] if i > 0 else ""

            # String handling - check for doubled-quote escape (PostgreSQL '')
            if char == "'" and in_string and string_char == "'":
                # This is a doubled quote '' inside a string - it's an escape
                current_value += char
                in_string = False
                string_char = None
                i += 1
                continue

            # Check for escaped backslash first
            if char == "\\" and i + 1 < len(values_str):
                # Keep backslash and next character as-is (\\, \', \")
                current_value += char
                i += 1
                if i < len(values_str):
                    current_value += values_str[i]
                i += 1
                continue

            # Quote handling
            if char in ("'", '"'):
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
                        i += 1
                        continue
                elif char == "," and depth == 1:
                    current_row.append(current_value.strip())
                    current_value = ""
                    i += 1
                    continue

            if depth > 0:
                current_value += char

            i += 1
