# client.py
import json
import socket
import threading
import pygame
from typing import Optional, Dict, Tuple

WIDTH, HEIGHT = 720, 720
GRID_COLOR = (30, 30, 30)
THICK = 6
THIN = 2
BG = (245, 245, 245)
X_COLOR = (40, 40, 200)
O_COLOR = (200, 40, 40)
Z_COLOR = (40, 160, 40)
FORCE_COLOR = (220, 220, 140)

# IMPORTANT:
# on Laptop A (Windows): set this to "127.0.0.1"
# on Laptop B (Mac): set this to the Windows IP, e.g. "10.54.99.254"
HOST = "10.54.99.254"
PORT = 8765

def send(sock, payload: Dict):
    try:
        sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
    except OSError:
        pass

def recv_thread(sock, on_msg):
    buf = b""
    while True:
        try:
            c = sock.recv(1)
        except OSError:
            break
        if not c:
            break
        if c == b"\n":
            try:
                on_msg(json.loads(buf.decode("utf-8")))
            except:
                pass
            buf = b""
        else:
            buf += c

class ClientState:
    def __init__(self):
        self.you_are: Optional[str] = None  # "X","O","Z","SPECTATOR"
        self.turn: str = "X"
        self.board = None  # dict from server
        self.last_error: Optional[str] = None
        self.required_players: int = 2
        self.connected_players: int = 0

    def handle(self, msg: Dict):
        t = msg.get("type")
        if t == "assign":
            self.you_are = msg.get("you_are")
            self.required_players = msg.get("required_players", 2)
            self.connected_players = msg.get("connected_players", 1)
        elif t == "state":
            self.turn = msg.get("turn")
            self.board = msg.get("board")
            self.required_players = msg.get("required_players", self.required_players)
            self.connected_players = msg.get("connected_players", self.connected_players)
            self.last_error = None
        elif t == "error":
            self.last_error = msg.get("message")

def draw_text(screen, text, size, color, center):
    font = pygame.font.SysFont(None, size)
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=center)
    screen.blit(surf, rect)

def draw_board(screen, st: ClientState):
    screen.fill(BG)

    # if we don't have the board yet
    if not st.board:
        draw_text(
            screen,
            f"Waiting for server... ({st.connected_players}/{st.required_players})",
            28,
            (0, 0, 0),
            (WIDTH // 2, HEIGHT // 2),
        )
        return

    # if not enough players yet
    if st.connected_players < st.required_players:
        draw_text(
            screen,
            f"Waiting for players... ({st.connected_players}/{st.required_players})",
            28,
            (0, 0, 0),
            (WIDTH // 2, 40),
        )

    cell = WIDTH // 3
    forced = st.board["next_forced"]
    if forced >= 0:
        fx = (forced % 3) * cell
        fy = (forced // 3) * cell
        pygame.draw.rect(screen, FORCE_COLOR, (fx, fy, cell, cell))

    # thick lines
    for i in range(4):
        x = i * cell
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT), THICK)
        pygame.draw.line(screen, GRID_COLOR, (0, x), (WIDTH, x), THICK)

    small = cell // 3
    # thin lines
    for by in range(3):
        for bx in range(3):
            base_x = bx * cell
            base_y = by * cell
            for j in range(1, 3):
                pygame.draw.line(
                    screen,
                    GRID_COLOR,
                    (base_x + j * small, base_y),
                    (base_x + j * small, base_y + cell),
                    THIN,
                )
                pygame.draw.line(
                    screen,
                    GRID_COLOR,
                    (base_x, base_y + j * small),
                    (base_x + cell, base_y + j * small),
                    THIN,
                )

    grids = st.board["grids"]
    winners = st.board["grid_winners"]
    for b in range(9):
        bx, by = (b % 3), (b // 3)
        base_x = bx * cell
        base_y = by * cell
        if winners[b] in ("X", "O", "Z", "T"):
            shade = 230 if winners[b] == "T" else 210
            pygame.draw.rect(screen, (shade, shade, shade), (base_x, base_y, cell, cell))
        for i in range(9):
            cx, cy = (i % 3), (i // 3)
            cxpix = base_x + cx * small + small // 2
            cypix = base_y + cy * small + small // 2
            val = grids[b][i]
            if val == "X":
                pygame.draw.line(screen, X_COLOR, (cxpix - 12, cypix - 12), (cxpix + 12, cypix + 12), 3)
                pygame.draw.line(screen, X_COLOR, (cxpix + 12, cypix - 12), (cxpix - 12, cypix + 12), 3)
            elif val == "O":
                pygame.draw.circle(screen, O_COLOR, (cxpix, cypix), 14, 3)
            elif val == "Z":
                # simple Z
                draw_text(screen, "Z", 26, Z_COLOR, (cxpix, cypix))

def pixel_to_move(mx, my) -> Tuple[int, int]:
    cell = WIDTH // 3
    small = cell // 3
    big_x = mx // cell
    big_y = my // cell
    small_x = (mx % cell) // small
    small_y = (my % cell) // small
    big = big_y * 3 + big_x
    small_idx = small_y * 3 + small_x
    return big, small_idx

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ultimate Tic Tac Toe (Client)")
    clock = pygame.time.Clock()

    st = ClientState()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    threading.Thread(target=recv_thread, args=(s, st.handle), daemon=True).start()

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and st.board:
                # only allowed if:
                # - we are X/O/Z
                # - and enough players have joined
                if st.you_are in ("X", "O", "Z"):
                    if st.connected_players >= st.required_players:
                        big, small = pixel_to_move(*e.pos)
                        send(s, {"type": "move", "big": big, "small": small})
                    else:
                        st.last_error = "Waiting for players..."
                else:
                    st.last_error = "You are a spectator"

        draw_board(screen, st)

        role = st.you_are or "?"
        info = f"You: {role} | Turn: {st.turn} | {st.connected_players}/{st.required_players}"
        draw_text(screen, info, 24, (0,0,0), (WIDTH//2, 20))

        if st.board:
            mw = st.board["macro_winner"]
            if mw:
                draw_text(screen, f"{mw} WINS!", 48, (0,128,0), (WIDTH//2, HEIGHT-30))
            elif st.board["macro_tied"]:
                draw_text(screen, "TIE", 48, (128,0,0), (WIDTH//2, HEIGHT-30))

        if st.last_error:
            draw_text(screen, st.last_error, 22, (160,0,0), (WIDTH//2, 50))

        pygame.display.flip()
        clock.tick(60)

    s.close()
    pygame.quit()

if __name__ == "__main__":
    main()
