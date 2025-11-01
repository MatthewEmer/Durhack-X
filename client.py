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
FORCE_COLOR = (220, 220, 140)

HOST = "10.247.14.144"   # change to server IP or ngrok host
PORT = 8765

def send(sock, payload: Dict):
    sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))

def recv_thread(sock, on_msg):
    buf = b""
    while True:
        c = sock.recv(1)
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
        self.you_are: Optional[str] = None  # "X"/"O"
        self.turn: str = "X"
        self.board = None  # dict from server
        self.last_error: Optional[str] = None

    def handle(self, msg: Dict):
        t = msg.get("type")
        if t == "assign":
            self.you_are = msg.get("you_are")
        elif t == "state":
            self.turn = msg.get("turn")
            self.board = msg.get("board")
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
    # outer grid (3x3)
    cell = WIDTH // 3
    # highlight forced board
    forced = st.board["next_forced"] if st.board else -1
    if forced >= 0:
        fx = (forced % 3) * cell
        fy = (forced // 3) * cell
        pygame.draw.rect(screen, FORCE_COLOR, (fx, fy, cell, cell))

    # thick lines for macro
    for i in range(4):
        x = i * cell
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT), THICK)
        pygame.draw.line(screen, GRID_COLOR, (0, x), (WIDTH, x), THICK)

    # thin lines for each small 3x3
    small = cell // 3
    for by in range(3):
        for bx in range(3):
            base_x = bx * cell
            base_y = by * cell
            for j in range(1,3):
                # vertical
                pygame.draw.line(screen, GRID_COLOR, (base_x + j*small, base_y), (base_x + j*small, base_y+cell), THIN)
                # horizontal
                pygame.draw.line(screen, GRID_COLOR, (base_x, base_y + j*small), (base_x+cell, base_y + j*small), THIN)

    # draw marks
    if not st.board:
        return
    grids = st.board["grids"]
    winners = st.board["grid_winners"]
    for b in range(9):
        bx, by = (b % 3), (b // 3)
        base_x = bx * cell
        base_y = by * cell
        # dim tied/won boards slightly
        if winners[b] in ("X", "O", "T"):
            shade = 230 if winners[b] == "T" else 210
            pygame.draw.rect(screen, (shade, shade, shade), (base_x, base_y, cell, cell))
        for i in range(9):
            cx, cy = (i % 3), (i // 3)
            cxpix = base_x + cx*small + small//2
            cypix = base_y + cy*small + small//2
            val = grids[b][i]
            if val == "X":
                pygame.draw.line(screen, X_COLOR, (cxpix-12, cypix-12), (cxpix+12, cypix+12), 3)
                pygame.draw.line(screen, X_COLOR, (cxpix+12, cypix-12), (cxpix-12, cypix+12), 3)
            elif val == "O":
                pygame.draw.circle(screen, O_COLOR, (cxpix, cypix), 14, 3)

def pixel_to_move(mx, my) -> Tuple[int,int]:
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
                big, small = pixel_to_move(*e.pos)
                send(s, {"type": "move", "big": big, "small": small})

        draw_board(screen, st)

        info = f"You: {st.you_are or '?'} | Turn: {st.turn}"
        draw_text(screen, info, 28, (0,0,0), (WIDTH//2, 20))

        if st.board:
            mw = st.board["macro_winner"]
            if mw:
                draw_text(screen, f"{mw} WINS!", 48, (0,128,0), (WIDTH//2, HEIGHT-30))
            elif st.board["macro_tied"]:
                draw_text(screen, "TIE", 48, (128,0,0), (WIDTH//2, HEIGHT-30))

        if st.last_error:
            draw_text(screen, st.last_error, 24, (160,0,0), (WIDTH//2, 50))

        pygame.display.flip()
        clock.tick(60)

    s.close()
    pygame.quit()

if __name__ == "__main__":
    main()
