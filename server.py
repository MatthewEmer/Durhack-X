import socket
import threading
import json
from typing import List, Dict, Optional, Tuple

HOST = "0.0.0.0"
PORT = 8765


def make_empty_board() -> Dict:
    # 9 small boards, each 9 cells
    return {
        "grids": [[None] * 9 for _ in range(9)],
        "next_forced": None,
        # we add this so the client can show big icons
        "big_wins": [None] * 9,
    }


class GameServer:
    def __init__(self, required_players: int = 2, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.required_players = required_players

        # players in seat order: X, O, Z
        self.marks = ["X", "O", "Z"]
        self.players: List[Dict] = []     # [{sock, name, mark}]
        self.spectators: List[Dict] = []  # [{sock, name}]
        self.lock = threading.Lock()

        self.board = make_empty_board()
        self.turn = "X"   # first player
        self.running = False

    # ============= networking =============
    def run(self):
        self.running = True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            while self.running:
                conn, addr = s.accept()
                t = threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
                t.start()

    def handle_client(self, conn: socket.socket, addr):
        buf = b""
        name_for_log = f"{addr}"

        def send_one(payload: Dict):
            try:
                conn.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            except OSError:
                pass

        try:
            while True:
                c = conn.recv(1)
                if not c:
                    break
                if c == b"\n":
                    try:
                        msg = json.loads(buf.decode("utf-8"))
                    except Exception:
                        buf = b""
                        continue
                    buf = b""

                    mtype = msg.get("type")
                    if mtype == "hello":
                        username = msg.get("name", "player")
                        name_for_log = username
                        self.register_client(conn, username, send_one)
                    elif mtype == "move":
                        big = msg.get("big")
                        small = msg.get("small")
                        self.handle_move(conn, big, small)
                else:
                    buf += c
        finally:
            self.remove_client(conn)

    # ============= registration =============
    def register_client(self, conn: socket.socket, username: str, send_one):
        with self.lock:
            if len(self.players) < self.required_players:
                mark = self.marks[len(self.players)]
                self.players.append({"sock": conn, "name": username, "mark": mark})
                # tell this client its seat
                send_one({
                    "type": "assign",
                    "you_are": mark,
                    "required_players": self.required_players,
                    "connected_players": len(self.players),
                    "player_names": {p["mark"]: p["name"] for p in self.players},
                    "spectator_names": [s["name"] for s in self.spectators],
                })
            else:
                # spectator
                self.spectators.append({"sock": conn, "name": username})
                send_one({
                    "type": "assign",
                    "you_are": None,
                    "required_players": self.required_players,
                    "connected_players": len(self.players),
                    "player_names": {p["mark"]: p["name"] for p in self.players},
                    "spectator_names": [s["name"] for s in self.spectators],
                })

            # broadcast current state to everyone
            self.broadcast_state_locked()

    def remove_client(self, conn: socket.socket):
        with self.lock:
            removed = False
            for i, p in enumerate(self.players):
                if p["sock"] is conn:
                    self.players.pop(i)
                    removed = True
                    break
            if not removed:
                for i, s in enumerate(self.spectators):
                    if s["sock"] is conn:
                        self.spectators.pop(i)
                        break
            self.broadcast_state_locked()

    # ============= broadcasting =============
    def broadcast_state_locked(self):
        payload = self.make_state_payload_locked()
        self.broadcast_locked(payload)

    def make_state_payload_locked(self) -> Dict:
        return {
            "type": "state",
            "turn": self.turn,
            "board": self.board,
            "required_players": self.required_players,
            "connected_players": len(self.players),
            "player_names": {p["mark"]: p["name"] for p in self.players},
            "spectator_names": [s["name"] for s in self.spectators],
        }

    def broadcast_locked(self, payload: Dict):
        dead = []
        for p in self.players:
            try:
                p["sock"].sendall((json.dumps(payload) + "\n").encode("utf-8"))
            except OSError:
                dead.append(p["sock"])
        for s in self.spectators:
            try:
                s["sock"].sendall((json.dumps(payload) + "\n").encode("utf-8"))
            except OSError:
                dead.append(s["sock"])
        # clean dead
        if dead:
            self.players = [p for p in self.players if p["sock"] not in dead]
            self.spectators = [s for s in self.spectators if s["sock"] not in dead]

    def broadcast_error_to(self, conn: socket.socket, msg: str):
        try:
            conn.sendall((json.dumps({"type": "error", "message": msg}) + "\n").encode("utf-8"))
        except OSError:
            pass

    # ============= game logic =============
    def handle_move(self, conn: socket.socket, big: int, small: int):
        with self.lock:
            # find which player this is
            player = self.get_player_by_sock_locked(conn)
            if player is None:
                self.broadcast_error_to(conn, "Spectators cannot move.")
                return

            mark = player["mark"]

            # must be that player's turn
            if mark != self.turn:
                self.broadcast_error_to(conn, "Not your turn.")
                return

            # players must all be present before we allow moves
            if len(self.players) < self.required_players:
                self.broadcast_error_to(conn, "Waiting for players.")
                return

            # apply move
            ok, errmsg = self.apply_move_locked(mark, big, small)
            if not ok:
                self.broadcast_error_to(conn, errmsg)
                return

            # rotate turn to next *seated* player
            self.turn = self.next_turn_locked(self.turn)

            # send out new state
            self.broadcast_state_locked()

    def get_player_by_sock_locked(self, conn: socket.socket) -> Optional[Dict]:
        for p in self.players:
            if p["sock"] is conn:
                return p
        return None

    def next_turn_locked(self, current_mark: str) -> str:
        marks_in_game = [p["mark"] for p in self.players]
        if current_mark not in marks_in_game:
            return marks_in_game[0]
        idx = marks_in_game.index(current_mark)
        idx = (idx + 1) % len(marks_in_game)
        return marks_in_game[idx]

    def apply_move_locked(self, mark: str, big: int, small: int) -> Tuple[bool, str]:
        # validate big/small
        if not (0 <= big < 9 and 0 <= small < 9):
            return False, "Invalid cell."

        grids = self.board["grids"]
        big_wins = self.board["big_wins"]
        next_forced = self.board["next_forced"]

        # is move allowed re. forced board?
        if next_forced is not None and next_forced != big:
            # BUT: if forced board is already won or full, move is free
            if not self.board_is_closed_locked(next_forced, grids, big_wins):
                return False, "Must play in forced board."

        # check target board not closed
        if self.board_is_closed_locked(big, grids, big_wins):
            return False, "That board is already closed."

        # check cell empty
        if grids[big][small] is not None:
            return False, "Cell occupied."

        # place move
        grids[big][small] = mark

        # after placing, see if that small board is now won (3-in-a-row, NORMAL)
        if self.check_small_win(grids[big], mark):
            big_wins[big] = mark

        # decide the next forced board:
        # if the board we point to is closed, then it's a free move
        if self.board_is_closed_locked(small, grids, big_wins):
            self.board["next_forced"] = None
        else:
            self.board["next_forced"] = small

        # NOW: check big-board win using your 2-in-a-row logic
        winner_big = self.check_big_win_two_in_row(big_wins)
        if winner_big:
            # we can store it in board for the clients
            self.board["big_winner"] = winner_big
            # you could also freeze moves here if you like
        else:
            self.board["big_winner"] = None

        return True, ""

    def board_is_closed_locked(self, idx: int, grids, big_wins) -> bool:
        # closed if already won or full
        if big_wins[idx] is not None:
            return True
        if all(c is not None for c in grids[idx]):
            return True
        return False

    @staticmethod
    def check_small_win(cells: List[Optional[str]], mark: str) -> bool:
        wins = [
            (0, 1, 2),
            (3, 4, 5),
            (6, 7, 8),
            (0, 3, 6),
            (1, 4, 7),
            (2, 5, 8),
            (0, 4, 8),
            (2, 4, 6),
        ]
        for a, b, c in wins:
            if cells[a] == mark and cells[b] == mark and cells[c] == mark:
                return True
        return False

    # =============== THIS IS THE IMPORTANT BIT ===============
    # === 2-IN-A-ROW BIG BOARD WIN, like your original code ===
    def check_big_win_two_in_row(self, big_wins: List[Optional[str]]) -> Optional[str]:
        """
        Your original local code was not '3 in a row' on the big board.
        It used a bunch of *pairs* like (0,1), (1,2), (3,4), ... and if both
        were owned by the same player, that player won the whole game.
        We'll copy that here.
        """
        # straight from your style:
        combos = [
            (0, 1), (1, 2),           # top row sliding
            (3, 4), (4, 5),           # middle row
            (6, 7), (7, 8),           # bottom row
            (0, 3), (3, 6),           # left column
            (1, 4), (4, 7),           # middle column
            (2, 5), (5, 8),           # right column
            (0, 4), (4, 8),           # main diagonal pairs
            (2, 4), (4, 6),           # other diagonal pairs
        ]
        for a, b in combos:
            if big_wins[a] is not None and big_wins[a] == big_wins[b]:
                return big_wins[a]
        return None
    # =============== END IMPORTANT BIT =======================


if __name__ == "__main__":
    # default: run 2-player server
    srv = GameServer(required_players=2)
    srv.run()
