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
    players: X,O,(Z)
    late joiners -> spectators

    EXTRA: if the HOST (first player, "X") sends {"type": "shutdown"},
    we broadcast "shutdown" to EVERYONE and stop.
    """
    def __init__(self, required_players: int = 2):
        assert required_players in (2, 3)
        self.required_players = required_players
        self.player_order: List[str] = ["X", "O"] if required_players == 2 else ["X", "O", "Z"]

        self.board = UltimateBoard()
        self.lock = threading.Lock()

        # mark -> socket
        self.players: Dict[str, socket.socket] = {}
        # mark -> username
        self.player_names: Dict[str, str] = {}

        # spectators
        self.spectators: List[socket.socket] = []
        self.spectator_names: Dict[int, str] = {}  # id(sock) -> name

        self.turn_index: int = 0
        self.running = True

    @property
    def current_turn(self) -> str:
        return self.player_order[self.turn_index]

    def next_turn(self):
        self.turn_index = (self.turn_index + 1) % len(self.player_order)

    # --------------------------------------------------
    # broadcast helpers
    # --------------------------------------------------
    def broadcast_state(self):
        state = {
            "type": "state",
            "turn": self.current_turn,
            "board": self.board.serialize(),
            "required_players": self.required_players,
            "connected_players": len(self.players),
            "players": list(self.players.keys()),
            "player_names": self.player_names,
            "spectator_names": list(self.spectator_names.values()),
        }

        # players
        dead_players = []
        for mark, sock in self.players.items():
            try:
                send(sock, state)
            except OSError:
                dead_players.append(mark)
        for mark in dead_players:
            if mark in self.player_names:
                del self.player_names[mark]
            del self.players[mark]

        # spectators
        alive_specs = []
        for s in self.spectators:
            try:
                send(s, state)
                alive_specs.append(s)
            except OSError:
                sid = id(s)
                if sid in self.spectator_names:
                    del self.spectator_names[sid]
        self.spectators = alive_specs

    def broadcast_shutdown(self):
        payload = {"type": "shutdown"}
        # to players
        for sock in list(self.players.values()):
            send(sock, payload)
            try:
                sock.close()
            except:
                pass
        # to spectators
        for sock in list(self.spectators):
            send(sock, payload)
            try:
                sock.close()
            except:
                pass

        self.players.clear()
        self.spectators.clear()

    # --------------------------------------------------
    # client handler
    # --------------------------------------------------
    def handle_client(self, sock: socket.socket, role: str):
        # tell client what they are
        send(sock, {
            "type": "assign",
            "you_are": role,
            "required_players": self.required_players,
            "connected_players": len(self.players),
            "player_names": self.player_names,
            "spectator_names": list(self.spectator_names.values()),
        })
        self.broadcast_state()

        try:
            while self.running:
                msg = recv_line(sock)
                if msg is None:
                    break

                mtype = msg.get("type")

                # client introduces themselves
                if mtype == "hello":
                    name = msg.get("name", "").strip()
                    if role in self.player_order:
                        if name:
                            self.player_names[role] = name
                    else:
                        if name:
                            self.spectator_names[id(sock)] = name
                    self.broadcast_state()
                    continue

                # host says "shutdown" -> kill room
                if mtype == "shutdown":
                    # ONLY allow the very first player (host) to do this
                    host_mark = self.player_order[0]  # typically "X"
                    if role == host_mark:
                        self.running = False
                        self.broadcast_shutdown()
                        break
                    else:
                        # ignore if spectators or non-host try
                        send(sock, {"type": "error", "message": "Only host can end the lobby"})
                        continue

                if mtype == "move":
                    if role not in self.player_order:
                        send(sock, {"type": "error", "message": "You are a spectator"})
                        continue

                    # don't accept moves until all required are in
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

    # --------------------------------------------------
    # accept loop
    # --------------------------------------------------
    def accept_loop(self, server_sock: socket.socket):
        while self.running:
            try:
                client, addr = server_sock.accept()
            except OSError:
                break
            print(f"[SERVER] connection from {addr}")

            # choose role
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


if __name__ == "__main__":
    gs = GameServer(2)
    gs.run()
