import json
import socket
import threading
import pygame
from typing import Optional, Dict, Tuple

from server import GameServer

WIDTH, HEIGHT = 720, 720
GRID_COLOR = (30, 30, 30)
THICK = 6
THIN = 2
BG = (245, 245, 245)
X_COLOR = (40, 40, 200)
O_COLOR = (200, 40, 40)
Z_COLOR = (40, 160, 40)
FORCE_COLOR = (220, 220, 140)

PORT = 8765

SCREEN_MENU = "menu"
SCREEN_HOST_CHOICE = "host_choice"
SCREEN_IP_INPUT = "ip_input"
SCREEN_GAME = "game"

BACK_BTN_RECT = pygame.Rect(20, 20, 90, 36)
IP_BOX_RECT = pygame.Rect(120, 250, 480, 50)


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
        self.you_are: Optional[str] = None
        self.turn: str = "X"
        self.board = None
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


def draw_back_button(screen):
    pygame.draw.rect(screen, (210, 210, 210), BACK_BTN_RECT, border_radius=6)
    font = pygame.font.SysFont(None, 22)
    txt = font.render("Back", True, (0, 0, 0))
    rect = txt.get_rect(center=BACK_BTN_RECT.center)
    screen.blit(txt, rect)


def draw_board(screen, st: ClientState):
    screen.fill(BG)

    if not st.board:
        draw_text(
            screen,
            f"Waiting for server... ({st.connected_players}/{st.required_players})",
            28,
            (0, 0, 0),
            (WIDTH // 2, HEIGHT // 2),
        )
        return

    if st.connected_players < st.required_players:
        draw_text(
            screen,
            f"Waiting for players... ({st.connected_players}/{st.required_players})",
            26,
            (0, 0, 0),
            (WIDTH // 2, 30),
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


def start_server_in_thread(required_players: int):
    def run():
        gs = GameServer(required_players)
        gs.run()

    t = threading.Thread(target=run, daemon=True)
    t.start()


def connect_to_server(host: str, port: int, st: ClientState):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    threading.Thread(target=recv_thread, args=(s, st.handle), daemon=True).start()
    return s


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ultimate Tic Tac Toe")
    clock = pygame.time.Clock()

    screen_mode = SCREEN_MENU
    ip_text = ""
    ip_active = False  # we'll still accept keys, but this is for drawing
    client_socket = None
    client_state = ClientState()

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            # ====== MAIN MENU ======
            if screen_mode == SCREEN_MENU:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    # Host
                    if 200 <= mx <= 520 and 250 <= my <= 310:
                        screen_mode = SCREEN_HOST_CHOICE
                    # Join
                    if 200 <= mx <= 520 and 340 <= my <= 400:
                        screen_mode = SCREEN_IP_INPUT
                        ip_text = ""
                        ip_active = True  # auto-focus

            # ====== HOST CHOICE ======
            elif screen_mode == SCREEN_HOST_CHOICE:
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    screen_mode = SCREEN_MENU
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    if BACK_BTN_RECT.collidepoint(mx, my):
                        screen_mode = SCREEN_MENU
                    # 2 players
                    elif 200 <= mx <= 520 and 250 <= my <= 310:
                        start_server_in_thread(2)
                        client_state = ClientState()
                        try:
                            client_socket = connect_to_server("127.0.0.1", PORT, client_state)
                            screen_mode = SCREEN_GAME
                        except OSError:
                            screen_mode = SCREEN_MENU
                    # 3 players
                    elif 200 <= mx <= 520 and 340 <= my <= 400:
                        start_server_in_thread(3)
                        client_state = ClientState()
                        try:
                            client_socket = connect_to_server("127.0.0.1", PORT, client_state)
                            screen_mode = SCREEN_GAME
                        except OSError:
                            screen_mode = SCREEN_MENU

            # ====== IP INPUT ======
            elif screen_mode == SCREEN_IP_INPUT:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    if BACK_BTN_RECT.collidepoint(mx, my):
                        screen_mode = SCREEN_MENU
                        ip_active = False
                    elif IP_BOX_RECT.collidepoint(mx, my):
                        ip_active = True
                    else:
                        ip_active = False

                elif e.type == pygame.KEYDOWN:
                    # ESC → back
                    if e.key == pygame.K_ESCAPE:
                        screen_mode = SCREEN_MENU
                        ip_active = False
                    elif e.key == pygame.K_RETURN:
                        # try connect with whatever is in ip_text
                        target_ip = ip_text.strip()
                        if target_ip:
                            client_state = ClientState()
                            try:
                                client_socket = connect_to_server(target_ip, PORT, client_state)
                                screen_mode = SCREEN_GAME
                                ip_active = False
                            except OSError:
                                # failed → stay here
                                ip_text = ""
                                ip_active = True
                    else:
                        # we always accept typing on this screen, to make it forgiving
                        if e.key == pygame.K_BACKSPACE:
                            ip_text = ip_text[:-1]
                        else:
                            # allow numbers, dot, colon (in case)
                            if e.unicode.isdigit() or e.unicode in (".", ":"):
                                ip_text += e.unicode

            # ====== GAME ======
            elif screen_mode == SCREEN_GAME:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and client_state.board:
                    if client_state.you_are in ("X", "O", "Z") and client_state.connected_players >= client_state.required_players:
                        big, small = pixel_to_move(*e.pos)
                        send(client_socket, {"type": "move", "big": big, "small": small})
                    else:
                        if client_state.connected_players < client_state.required_players:
                            client_state.last_error = "Waiting for players..."
                        else:
                            client_state.last_error = "You are a spectator"

        # ===== DRAW =====
        if screen_mode == SCREEN_MENU:
            screen.fill((230, 230, 230))
            draw_text(screen, "Ultimate Tic Tac Toe", 48, (0, 0, 0), (WIDTH // 2, 120))

            pygame.draw.rect(screen, (200, 200, 255), (200, 250, 320, 60))
            draw_text(screen, "Host a game", 30, (0, 0, 80), (WIDTH // 2, 280))

            pygame.draw.rect(screen, (200, 255, 200), (200, 340, 320, 60))
            draw_text(screen, "Join a game", 30, (0, 80, 0), (WIDTH // 2, 370))

        elif screen_mode == SCREEN_HOST_CHOICE:
            screen.fill((230, 230, 230))
            draw_text(screen, "Host: choose players", 40, (0, 0, 0), (WIDTH // 2, 120))
            draw_back_button(screen)

            pygame.draw.rect(screen, (200, 200, 255), (200, 250, 320, 60))
            draw_text(screen, "2 players", 30, (0, 0, 80), (WIDTH // 2, 280))

            pygame.draw.rect(screen, (200, 200, 255), (200, 340, 320, 60))
            draw_text(screen, "3 players", 30, (0, 0, 80), (WIDTH // 2, 370))

        elif screen_mode == SCREEN_IP_INPUT:
            screen.fill((230, 230, 230))
            draw_text(screen, "Enter host IP", 40, (0, 0, 0), (WIDTH // 2, 120))

            draw_back_button(screen)

            # input box
            pygame.draw.rect(screen, (255, 255, 255), IP_BOX_RECT)
            border_color = (0, 120, 0) if ip_active else (120, 120, 120)
            pygame.draw.rect(screen, border_color, IP_BOX_RECT, 2)

            # text
            font = pygame.font.SysFont(None, 30)
            txt_surf = font.render(ip_text, True, (0, 0, 0))
            screen.blit(txt_surf, (IP_BOX_RECT.x + 8, IP_BOX_RECT.y + 12))

            # caret
            if ip_active:
                caret_x = IP_BOX_RECT.x + 8 + txt_surf.get_width() + 2
                caret_y1 = IP_BOX_RECT.y + 8
                caret_y2 = IP_BOX_RECT.y + IP_BOX_RECT.height - 8
                pygame.draw.line(screen, (0, 120, 0), (caret_x, caret_y1), (caret_x, caret_y2), 2)

            draw_text(
                screen,
                "Type IP, press Enter to connect, ESC/Back to cancel",
                18,
                (0, 0, 0),
                (WIDTH // 2, 340),
            )

        elif screen_mode == SCREEN_GAME:
            draw_board(screen, client_state)
            role = client_state.you_are or "?"
            info = f"You: {role} | Turn: {client_state.turn} | {client_state.connected_players}/{client_state.required_players}"
            draw_text(screen, info, 22, (0, 0, 0), (WIDTH // 2, 12))
            if client_state.last_error:
                draw_text(screen, client_state.last_error, 20, (160, 0, 0), (WIDTH // 2, HEIGHT - 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
