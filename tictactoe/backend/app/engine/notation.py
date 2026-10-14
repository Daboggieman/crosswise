COLUMNS = ("A", "B", "C")
ROWS = (1, 2, 3)

class InvalidNotationError(Exception):
    pass

def index_to_coord(index: int) -> tuple[str, int]:
    if index < 0 or index > 8:
        raise InvalidNotationError("Cell must be between 0 and 8.")
    return (COLUMNS[index % 3], ROWS[index // 3])

def coord_to_index(column: str, row: int) -> int:
    column = column.upper()
    if column not in COLUMNS or row not in ROWS:
        raise InvalidNotationError("Coordinates must be A1 to C3.")
    return COLUMNS.index(column) + (row - 1) * 3

def index_to_notation(index: int) -> str:
    column, row = index_to_coord(index)
    return f"{column}{row}"

def notation_to_index(value: str) -> int:
    value = value.strip().upper()
    if len(value) != 2:
        raise InvalidNotationError("Notation must be a column letter and row number, like A1.")
    column, row = value[0], value[1]
    if not row.isdigit():
        raise InvalidNotationError("The second character must be a row number, 1 to 3.")
    return coord_to_index(column, int(row))
