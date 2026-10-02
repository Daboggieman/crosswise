from app.engine.board import board_from_string, board_to_string, winning_triples

def test_board_string_roundtrip():
    s = "XOX--O-X."
    cells = board_from_string(s)
    result = board_to_string(cells)
    assert result == s
