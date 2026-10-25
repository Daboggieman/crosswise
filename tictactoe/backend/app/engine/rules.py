from app.engine.board import (
    State,
    empty,
    mark_O,
    mark_X,
    status_drawn,
    status_in_progress,
    status_won,
    winning_triples,
)


def new_game():
    return State()

def legal_moves(state: State):
    if state.status != status_in_progress:
        return []

    return [
        index
        for index, cell in enumerate(state.board)
        if cell == empty
    ]

class InvalidCellError(Exception):
    pass


class OccupiedCellError(Exception):
    pass


class WrongTurnError(Exception):
    pass


class GameOverError(Exception):
    pass


def other_player(player: str):
    if player not in (mark_X, mark_O):
        raise ValueError("Player must be X or O.")
    if player == mark_X:
        return mark_O
    else:
        return mark_X


def apply_move(state: State, player: str, cell: int):
    if state.status != status_in_progress:
            raise GameOverError("The game is already over.")
    
    if cell < 0 or cell > 8:
        raise InvalidCellError("Cell must be between 0 and 8.")

    if state.board[cell] != empty:
        raise OccupiedCellError("Cell is already occupied.")

    if state.turn != player:
        raise WrongTurnError("It is not this player's turn.")


    new_board = state.board[:cell] + (player,) + state.board[cell + 1:]

    new_state = State(
        board=new_board,
        turn=other_player(player)
    )
    return evaluate(new_state)


def evaluate(state: State) -> State:
    for mark in (mark_X, mark_O):
        for line in winning_triples:
            if all(state.board[index] == mark for index in line):
                return State(
                    board=state.board,
                    turn=state.turn,
                    winner=mark,
                    line=line,
                    status=status_won
                )

    if empty not in state.board:
        return State(
            board=state.board,
            turn=state.turn,
            winner=None,
            line=None,
            status=status_drawn
        )

    return state

def replay(moves:list[int]):
    state = new_game()
    if moves is None:
        moves = []
    for cell in moves:
        state = apply_move(state, state.turn, cell)
    return state