# server.py
import json
import socket
import threading
from typing import Dict, Tuple, Optional

from common import UltimateBoard

HOST = "0.0.0.0"
PORT = 8765

# Message helpers: newline-delimited JSON
def send(sock: socket.socket, payload: Dict):
    data = (json.dumps(payload) + "\n").encode("utf-8")
    sock.sendall(data)

def recv_line(sock: socket.socket) -> Optional[Dict]:
    buf = b""
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

class GameServer:
    def __init__(self):
        self.board = UltimateBoard()
        self.lock = threading.Lock()
        self.players: Dict[str, socket.socket] = {}  # "X" -> socket, "O" -> socket
        self.turn: str = "X"
        self.running = True

    def broadcast_state(self):
        state = {
            "type": "state",
            "turn": self.turn,
            "board": self.board.serialize()
        }
        for s in self.players.values():
            send(s, state)

    def client_thread(self, sock: socket.socket, role: str):
        send(sock, {"type": "assign", "you_are": role})
        self.broadcast_state()
        try:
            while self.running:
                msg = recv_line(sock)
                if msg is None:
                    break
                if msg.get("type") == "move":
                    b = int(msg.get("big", -1))
                    i = int(msg.get("small", -1))
                    with self.lock:
                        if role != self.turn:
                            send(sock, {"type": "error", "message": "Not your turn"})
                            continue
                        ok = self.board.apply(self.turn, (b, i))
                        if not ok:
                            send(sock, {"type": "error", "message": "Illegal move"})
                            continue
                        # swap turns if game not over
                        if not self.board.macro_winner and not self.board.macro_tied:
                            self.turn = "O" if self.turn == "X" else "X"
                    self.broadcast_state()
        finally:
            try:
                sock.close()
            except:
                pass

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, PORT))
            server.listen(2)
            print(f"[SERVER] Listening on {HOST}:{PORT}")

            # accept 2 players
            conn1, addr1 = server.accept()
            print(f"[SERVER] Player X connected from {addr1}")
            self.players["X"] = conn1
            send(conn1, {"type": "welcome", "need": "waiting-for-opponent"})

            conn2, addr2 = server.accept()
            print(f"[SERVER] Player O connected from {addr2}")
            self.players["O"] = conn2
            send(conn2, {"type": "welcome", "need": "start"})

            t1 = threading.Thread(target=self.client_thread, args=(conn1,"X"), daemon=True)
            t2 = threading.Thread(target=self.client_thread, args=(conn2,"O"), daemon=True)
            t1.start()
            t2.start()

            # Keep main thread alive until both sockets die
            t1.join()
            t2.join()
            print("[SERVER] Both clients disconnected; shutting down")

if __name__ == "__main__":
    GameServer().run()
