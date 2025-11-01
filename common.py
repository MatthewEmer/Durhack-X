# common.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

# Players: 'X' and 'O'
Player = str
Move = Tuple[int, int]  # (big_idx 0..8, small_idx 0..8)

WIN_TRIPLES = [
    (0,1,2),(3,4,5),(6,7,8),  # rows
    (0,3,6),(1,4,7),(2,5,8),  # cols
    (0,4,8),(2,4,6)           # diags
]

def winner_of(cells: List[Optional[Player]]) -> Optional[Player]:
    for a,b,c in WIN_TRIPLES:
        if cells[a] and cells[a] == cells[b] == cells[c]:
            return cells[a]
    return None

def board_full(cells: List[Optional[Player]]) -> bool:
    return all(c is not None for c in cells)

@dataclass
class SmallBoard:
    cells: List[Optional[Player]] = field(default_factory=lambda: [None]*9)
    won_by: Optional[Player] = None
    tied: bool = False

    def play(self, p: Player, idx: int) -> bool:
        if self.won_by or self.tied: return False
        if not (0 <= idx < 9): return False
        if self.cells[idx] is not None: return False
        self.cells[idx] = p
        w = winner_of(self.cells)
        if w:
            self.won_by = w
        elif board_full(self.cells):
            self.tied = True
        return True

@dataclass
class UltimateBoard:
    grids: List[SmallBoard] = field(default_factory=lambda: [SmallBoard() for _ in range(9)])
    macro: List[Optional[Player]] = field(default_factory=lambda: [None]*9)  # who won each small board (cached)
    macro_winner: Optional[Player] = None
    macro_tied: bool = False
    next_forced: Optional[int] = None  # which small board index must be played next; None means free choice

    def _update_macro(self):
        for i, sb in enumerate(self.grids):
            self.macro[i] = sb.won_by if sb.won_by else (None if not sb.tied else 'T')  # 'T' to mark tied boards
        # A macro square counts as owned by the winner only, ties don't help win macro
        macro_cells = [g.won_by for g in self.grids]
        w = winner_of(macro_cells)
        if w:
            self.macro_winner = w
            return
        # full macro tie?
        if all(g.won_by or g.tied for g in self.grids):
            self.macro_tied = True

    def legal_moves(self, player_to_move: Player) -> List[Move]:
        if self.macro_winner or self.macro_tied:
            return []
        boards_to_consider = range(9) if self.next_forced is None else [self.next_forced]
        moves: List[Move] = []
        for b in boards_to_consider:
            sb = self.grids[b]
            if sb.won_by or sb.tied: 
                continue
            for i in range(9):
                if sb.cells[i] is None:
                    moves.append((b, i))
        # If forced board is closed, player can play anywhere open
        if not moves and self.next_forced is not None:
            for b in range(9):
                sb = self.grids[b]
                if sb.won_by or sb.tied: 
                    continue
                for i in range(9):
                    if sb.cells[i] is None:
                        moves.append((b, i))
        return moves

    def apply(self, player_to_move: Player, move: Move) -> bool:
        b, i = move
        # Validate move
        legal = self.legal_moves(player_to_move)
        if move not in legal:
            return False
        # Play
        ok = self.grids[b].play(player_to_move, i)
        if not ok: 
            return False
        # Update macro status
        self._update_macro()
        # Set next forced board
        self.next_forced = i
        # If next forced board is already won/tied/full -> free choice next
        sb = self.grids[self.next_forced]
        if sb.won_by or sb.tied or board_full(sb.cells):
            self.next_forced = None
        return True

    def serialize(self) -> Dict:
        return {
            "grids": [[cell if cell is not None else "" for cell in sb.cells] for sb in self.grids],
            "grid_winners": [g.won_by if g.won_by else ("" if not g.tied else "T") for g in self.grids],
            "macro_winner": self.macro_winner or "",
            "macro_tied": self.macro_tied,
            "next_forced": self.next_forced if self.next_forced is not None else -1,
        }
