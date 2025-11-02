"""
Shared game logic for Ultimate Tic Tac Toe.
Used by both server.py and client.py.

Board layout:
- 9 big boards (index 0..8), arranged 3x3
- each big board has 9 cells (index 0..8), arranged 3x3

NEW MACRO RULE (2025-11-02):
- a player wins the macro board if they own **2 adjacent** big squares
  (horizontal, vertical, or diagonal)
- if all 9 small boards are decided (won or tied) and nobody has 2 adjacent,
  the macro board is tied.
"""

from typing import List, Optional, Tuple


# normal small-board win lines (3 in a row)
WIN_LINES = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
]

# NEW: macro board checks *adjacent pairs*, not 3-in-a-row
# indices:
#   0 1 2
#   3 4 5
#   6 7 8
ADJACENT_MACRO_PAIRS = [
    # rows
    (0, 1), (1, 2),
    (3, 4), (4, 5),
    (6, 7), (7, 8),
    # columns
    (0, 3), (3, 6),
    (1, 4), (4, 7),
    (2, 5), (5, 8),
    # diagonals through centre
    (0, 4), (4, 8),
    (2, 4), (4, 6),
]


class SmallBoard:
    def __init__(self):
        # 9 cells, "" means empty
        self.cells: List[str] = [""] * 9
        self.winner: str = ""  # "X","O","Z","T",""
        self.tied: bool = False

    def is_full(self) -> bool:
        return all(c != "" for c in self.cells)

    def apply(self, mark: str, idx: int) -> bool:
        """Attempt to place mark at cell idx (0..8). Return True if success."""
        if not (0 <= idx < 9):
            return False
        if self.cells[idx] != "":
            return False
        if self.winner:
            return False
        self.cells[idx] = mark
        self._update_status()
        return True

    def _update_status(self):
        # check win
        for a, b, c in WIN_LINES:
            if self.cells[a] and self.cells[a] == self.cells[b] == self.cells[c]:
                self.winner = self.cells[a]
                return
        # check tie
        if self.is_full() and not self.winner:
            self.tied = True
            self.winner = "T"  # tie

    def serialize(self) -> List[str]:
        return list(self.cells)


class UltimateBoard:
    def __init__(self):
        self.boards: List[SmallBoard] = [SmallBoard() for _ in range(9)]
        self.grid_winners: List[str] = [""] * 9  # each is "", "X","O","Z","T"
        self.macro_winner: str = ""  # if someone wins macro
        self.macro_tied: bool = False
        # -1 means "free move" (no forced board)
        self.next_forced: int = -1

    def _update_macro(self):
        """
        Update macro win/tie based on NEW RULE:
        - if any *adjacent pair* of small boards is won by the same real player (not "T"),
          that player wins the macro board
        - otherwise, if all 9 small boards are decided (winner or T) -> macro_tied
        """
        # update list of per-board winners
        for i, sb in enumerate(self.boards):
            self.grid_winners[i] = sb.winner

        # check adjacent pairs (our new win condition)
        for a, b in ADJACENT_MACRO_PAIRS:
            wa = self.grid_winners[a]
            wb = self.grid_winners[b]
            if wa and wa == wb and wa != "T":
                self.macro_winner = wa
                self.macro_tied = False
                return

        # if no winner, see if everything is decided -> tie
        if all(w != "" for w in self.grid_winners):
            self.macro_tied = True
        else:
            self.macro_tied = False

    def apply(self, mark: str, move: Tuple[int, int]) -> bool:
        """
        move = (big_idx, small_idx)
        Enforces forced-board rule:
          - if next_forced >=0 and that board is still playable, you MUST play there
          - otherwise you can play anywhere valid
        Returns True if move applied.
        """
        big_idx, small_idx = move

        # basic bounds check
        if not (0 <= big_idx < 9 and 0 <= small_idx < 9):
            return False

        # if there is a forced board, check it is still active
        if self.next_forced >= 0:
            forced_board = self.boards[self.next_forced]
            # if forced board is still playable, you must play there
            if not forced_board.winner and not forced_board.tied:
                if big_idx != self.next_forced:
                    return False
            else:
                # forced board is dead, so the player can play anywhere
                self.next_forced = -1

        # now actually try to apply to chosen board
        board = self.boards[big_idx]
        ok = board.apply(mark, small_idx)
        if not ok:
            return False

        # after a move, work out next forced board
        target_board = self.boards[small_idx]
        if not target_board.winner and not target_board.tied:
            self.next_forced = small_idx
        else:
            self.next_forced = -1

        # update macro using NEW rule
        self._update_macro()
        return True

    def serialize(self) -> dict:
        """
        Return a JSON-serializable snapshot for clients.
        """
        return {
            "grids": [sb.serialize() for sb in self.boards],
            "grid_winners": list(self.grid_winners),
            "next_forced": self.next_forced,
            "macro_winner": self.macro_winner,
            "macro_tied": self.macro_tied,
        }
