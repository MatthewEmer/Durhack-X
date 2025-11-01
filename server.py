# server.py
import json
import socket
import threading
from typing import Dict, Optional, List

from common import UltimateBoard

HOST = "0.0.0.0"
PORT = 8765

def send(sock: socket.socket, payload: Dict):
    try:
        data = (json.dumps(payload) + "\n").encode("utf-8")
        sock.sendall(data)
    except OSError:
        pass

def recv_line(sock: socket.socket) -> Optional[Dict]:
    buf = b""
    try:
        while True:
            chunk = sock.recv(1)
            if not chunk:
                return None
            if chunk == b"\n":
                try:
                    return json.loads(buf.decode("utf-8"))
                except json.JSONDecodeError:
                    return None
            buf += chunk
    except OSError:
        return None


class GameServer:
    """
    Host-side server.
    required_players: 2 or 3
    players will be: ["X", "O"] or ["X", "O", "Z"]
    everyone else => spectator
    """
    def __init__(self, required_players: int = 2):
        assert required_players in (2, 3), "Only 2 or 3 players allowed"
        self.required_players = required_players
        self.player_order: List[str] = ["X", "O"] if required_players == 2 else ["X", "O", "Z"]

        self.board = UltimateBoard()
        self.lock = threading.Lock()

        self.players: Dict[str, socket.socket] = {}
        self.spectators: List[socket.socket] = []

        self.turn_index: int = 0
        self.running = True

    @property
    def current_turn(self) -> str:
        return self.player_order[self.turn_index]

    def next_turn(self):
        self.turn_index = (self.turn_index + 1) % len(self.player_order)

    def broadcast_state(self):
        state = {
            "type": "state",
            "turn": self.current_turn,
            "board": self.board.serialize(),
            "required_players": self.required_players,
            "connected_players": len(self.players),
            "players": list(self.players.keys()),
        }

        # players
        dead = []
        for mark, sock in self.players.items():
            try:
                send(sock, state)
            except OSError:
                dead.append(mark)
        for mark in dead:
            del self.players[mark]

        # spectators
        alive_specs = []
        for sock in self.spectators:
            try:
                send(sock, state)
                alive_specs.append(sock)
            except OSError:
                pass
        self.spectators = alive_specs

    def handle_client(self, sock: socket.socket, role: str):
        # first message: tell the client what they are
        send(sock, {
            "type": "assign",
            "you_are": role,
            "required_players": self.required_players,
            "connected_players": len(self.players),
        })
        self.broadcast_state()

        try:
            while self.running:
                msg = recv_line(sock)
                if msg is None:
                    break

                if msg.get("type") == "move":
                    # spectators can't move
                    if role not in self.player_order:
                        send(sock, {"type": "error", "message": "You are a spectator"})
                        continue

                    # if we don't have all players yet, no moves
                    if len(self.players) < self.required_players:
                        send(sock, {"type": "error", "message": "Waiting for more players"})
                        continue

                    big = int(msg.get("big", -1))
                    small = int(msg.get("small", -1))

                    with self.lock:
                        if role != self.current_turn:
                            send(sock, {"type": "error", "message": "Not your turn"})
                            continue

                        ok = self.board.apply(self.current_turn, (big, small))
                        if not ok:
                            send(sock, {"type": "error", "message": "Illegal move"})
                            continue

                        # advance turn if game not over
                        if not self.board.macro_winner and not self.board.macro_tied:
                            self.next_turn()

                    self.broadcast_state()
        finally:
            try:
                sock.close()
            except:
                pass

    def accept_loop(self, server_sock: socket.socket):
        while self.running:
            client, addr = server_sock.accept()
            print(f"[SERVER] connection from {addr}")

            if len(self.players) < self.required_players:
                role = self.player_order[len(self.players)]
                self.players[role] = client
                print(f"[SERVER] assigned {role}")
            else:
                role = "SPECTATOR"
                self.spectators.append(client)
                print("[SERVER] assigned SPECTATOR")

            t = threading.Thread(target=self.handle_client, args=(client, role), daemon=True)
            t.start()

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, PORT))
            server.listen(5)
            print(f"[SERVER] Listening on {HOST}:{PORT}")
            self.accept_loop(server)


# we still allow running it directly for testing
if __name__ == "__main__":
    gs = GameServer(2)
    gs.run()
