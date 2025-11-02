"""
Shared game logic for Ultimate Tic Tac Toe.
Used by both server.py and client.py.

Board layout:
- 9 big boards (index 0..8), arranged 3x3
- each big board has 9 cells (index 0..8), arranged 3x3

We track:
- per-small-board winner ("X","O","Z","T","")
- macro winner (someone wins 2 adjacent small boards, for our custom rule)
- next_forced: which big board the next player MUST play in

Extra for 3-player mode:
- if reset_on_tie=True, a small board that fills without a winner is cleared
  so that it can be claimed again later.
"""

from typing import List, Tuple


# normal 3x3 lines
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

# for the macro "two in a row" rule
ADJACENT_PAIRS = [
    # rows
    (0, 1), (1, 2),
    (3, 4), (4, 5),
    (6, 7), (7, 8),
    # cols
    (0, 3), (3, 6),
    (1, 4), (4, 7),
    (2, 5), (5, 8),
    # diagonals through middle
    (0, 4), (4, 8),
    (2, 4), (4, 6),
]


class SmallBoard:
    def __init__(self):
        # 9 cells, "" means empty
        self.cells: List[str] = [""] * 9
        self.winner: str = ""  # "X","O","Z","T",""
        self.tied: bool = False

    def clear(self):
        """Make this small board playable again."""
        self.cells = [""] * 9
        self.winner = ""
        self.tied = False

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
            self.winner = "T"  # tie-by-default (server may clear it later)

    def serialize(self) -> List[str]:
        return list(self.cells)


class UltimateBoard:
    def __init__(self, reset_on_tie: bool = False, win_rule: str = "adjacent-2"):
        """
        reset_on_tie:
            - False (2-player): a tied small board becomes dead ("T")
            - True  (3-player): a tied small board is immediately cleared so it can be won later
        win_rule:
            - just sent to the client so it can display it
        """
        self.boards: List[SmallBoard] = [SmallBoard() for _ in range(9)]
        self.grid_winners: List[str] = [""] * 9  # each is "", "X","O","Z","T"
        self.macro_winner: str = ""  # if someone wins on macro
        self.macro_tied: bool = False
        self.next_forced: int = -1  # -1 means "free"
        self.reset_on_tie = reset_on_tie
        self.win_rule = win_rule

    # -----------------------------------------------------
    # internal helpers
    # -----------------------------------------------------
    def _update_macro(self):
        # refresh per-board winners list
        for i, sb in enumerate(self.boards):
            self.grid_winners[i] = sb.winner

        # OUR RULE: win if you have 2 adjacent decided boards (not T)
        for a, b in ADJACENT_PAIRS:
            wa, wb = self.grid_winners[a], self.grid_winners[b]
            if wa and wb and wa == wb and wa != "T":
                self.macro_winner = wa
                return

        # macro tie: only if ALL 9 small boards are decided (winner or T) and no macro winner
        if all(w != "" for w in self.grid_winners) and not self.macro_winner:
            self.macro_tied = True

    # -----------------------------------------------------
    # public API
    # -----------------------------------------------------
    def apply(self, mark: str, move: Tuple[int, int]) -> bool:
        """
        move = (big_idx, small_idx)
        Enforces forced-board rule:
          - if next_forced >=0 and that board is still playable, you MUST play there
          - otherwise you can play anywhere valid
        Returns True if move applied.
        """
        big_idx, small_idx = move

        if not (0 <= big_idx < 9 and 0 <= small_idx < 9):
            return False

        # if there is a forced board, check it is still active
        if self.next_forced >= 0:
            forced_board = self.boards[self.next_forced]
            if not forced_board.winner and not forced_board.tied:
                # you MUST play there
                if big_idx != self.next_forced:
                    return False
            else:
                # forced board is dead, so the player can play anywhere
                self.next_forced = -1

        board = self.boards[big_idx]
        ok = board.apply(mark, small_idx)
        if not ok:
            return False

        # if this move caused a tie on this small board
        if board.tied and self.reset_on_tie:
            # 3-player mode: wipe it — this board is still claimable later
            board.clear()
            self.grid_winners[big_idx] = ""
        else:
            # normal flow: decide where the next player must go
            target_board = self.boards[small_idx]
            if not target_board.winner and not target_board.tied:
                self.next_forced = small_idx
            else:
                self.next_forced = -1

        # now recalc macro (with our 2-adjacent rule)
        self._update_macro()
        return True

    def serialize(self) -> dict:
        return {
            "grids": [sb.serialize() for sb in self.boards],
            "grid_winners": list(self.grid_winners),
            "next_forced": self.next_forced,
            "macro_winner": self.macro_winner,
            "macro_tied": self.macro_tied,
            "win_rule": self.win_rule,
        }
