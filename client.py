import json
import socket
import threading
import pygame
import os
from typing import Optional, Dict, Tuple

from server import GameServer  # your existing server.py

# =========================================================
# CONFIG
# =========================================================
WIDTH, HEIGHT = 720, 720
PORT = 8765  # keep this the same on all laptops

# screens
SCREEN_USERNAME = "username"
SCREEN_MENU = "menu"
SCREEN_HOST_CHOICE = "host_choice"
SCREEN_IP_INPUT = "ip_input"
SCREEN_HOST_LOBBY = "host_lobby"
SCREEN_GAME = "game"

# ---------------------------------------------------------
# DARK PALETTE
# ---------------------------------------------------------
# background layers
COLOR_BG = (15, 23, 42)          # main background (slate-900)
COLOR_PANEL = (30, 41, 59)       # panels / cards (slate-800)
COLOR_PANEL_LIGHT = (51, 65, 85) # slightly lighter (slate-700)
COLOR_INPUT_BG = (15, 23, 42)    # input background
COLOR_BORDER = (71, 85, 105)     # grey border
# text
COLOR_TEXT = (248, 250, 252)     # near-white
COLOR_MUTED = (148, 163, 184)    # slate-400
# accents
COLOR_ACCENT = (56, 189, 248)    # sky-400
COLOR_ACCENT_DARK = (8, 47, 73)  # dark blue for pressed

# fonts will be made after pygame.init()


# =========================================================
# NETWORK HELPERS
# =========================================================
def send(sock: socket.socket, payload: dict):
    try:
        sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
    except OSError:
        pass


def recv_thread(sock: socket.socket, on_msg):
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
                msg = json.loads(buf.decode("utf-8"))
                on_msg(msg)
            except Exception:
                pass
            buf = b""
        else:
            buf += c


def start_server_in_thread(required_players: int):
    def run():
        gs = GameServer(required_players)
        gs.run()
    t = threading.Thread(target=run, daemon=True)
    t.start()


def connect_to_server(host: str, port: int, state, username: str) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    threading.Thread(target=recv_thread, args=(s, state.handle), daemon=True).start()
    send(s, {"type": "hello", "name": username})
    return s


def get_local_ip() -> str:
    """Try to get a usable LAN / hotspot address."""
    try:
        tmp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tmp.connect(("8.8.8.8", 80))
        ip = tmp.getsockname()[0]
        tmp.close()
        return ip
    except OSError:
        return "127.0.0.1"


# =========================================================
# CLIENT STATE (comes from server)
# =========================================================
class ClientState:
    def __init__(self):
        self.you_are: Optional[str] = None  # "X" / "O" / "Z"
        self.turn: str = "X"
        self.board = None  # dict from server
        self.required_players: int = 2
        self.connected_players: int = 0
        self.player_names: Dict[str, str] = {}
        self.spectator_names = []
        self.last_error: Optional[str] = None

    def handle(self, msg: Dict):
        t = msg.get("type")
        if t == "assign":
            self.you_are = msg.get("you_are")
            self.required_players = msg.get("required_players", 2)
            self.connected_players = msg.get("connected_players", 1)
            self.player_names = msg.get("player_names", {})
            self.spectator_names = msg.get("spectator_names", [])
        elif t == "state":
            self.turn = msg.get("turn")
            self.board = msg.get("board")
            self.required_players = msg.get("required_players", self.required_players)
            self.connected_players = msg.get("connected_players", self.connected_players)
            self.player_names = msg.get("player_names", self.player_names)
            self.spectator_names = msg.get("spectator_names", self.spectator_names)
            self.last_error = None
        elif t == "error":
            self.last_error = msg.get("message")


# =========================================================
# UI HELPERS
# =========================================================
def load_image(path: str):
    if not os.path.exists(path):
        return None
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None


def draw_button(screen, rect, text, font, variant="normal"):
    if variant == "primary":
        bg = COLOR_ACCENT
        fg = (10, 22, 33)
    else:
        bg = COLOR_PANEL_LIGHT
        fg = COLOR_TEXT

    pygame.draw.rect(screen, bg, rect, border_radius=16)
    pygame.draw.rect(screen, (12, 17, 26), rect, 1, border_radius=16)
    txt = font.render(text, True, fg)
    screen.blit(txt, txt.get_rect(center=rect.center))


def draw_input(screen, rect, text, font, placeholder=""):
    pygame.draw.rect(screen, COLOR_INPUT_BG, rect, border_radius=14)
    pygame.draw.rect(screen, COLOR_BORDER, rect, 1, border_radius=14)
    shown = text if text else placeholder
    col = COLOR_TEXT if text else COLOR_MUTED
    surf = font.render(shown, True, col)
    screen.blit(surf, (rect.x + 10, rect.y + (rect.height - surf.get_height()) // 2))


# =========================================================
# GAME BOARD DRAW
# =========================================================
def draw_board(screen, st: ClientState, board_img, x_img, o_img, z_img, font_small):
    # background for game
    screen.fill((15, 23, 42))  # slate-900

    if not st.board:
        msg = f"Waiting for players... {st.connected_players}/{st.required_players}"
        surf = font_small.render(msg, True, COLOR_TEXT)
        screen.blit(surf, surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        return

    cell = WIDTH // 3
    small = cell // 3

    # forced board highlight
    forced = st.board["next_forced"]
    if forced is not None:
        fx = (forced % 3) * cell
        fy = (forced // 3) * cell
        pygame.draw.rect(screen, (30, 64, 175), (fx, fy, cell, cell))

    # draw 9 boards
    for b in range(9):
        bx = (b % 3) * cell
        by = (b // 3) * cell
        if board_img:
            screen.blit(pygame.transform.smoothscale(board_img, (cell, cell)), (bx, by))
        else:
            # dark board fallback
            pygame.draw.rect(screen, (15, 23, 42), (bx, by, cell, cell))
            pygame.draw.rect(screen, (51, 65, 85), (bx, by, cell, cell), 2)
            for j in range(1, 3):
                pygame.draw.line(screen, (71, 85, 105), (bx + j * small, by), (bx + j * small, by + cell), 2)
                pygame.draw.line(screen, (71, 85, 105), (bx, by + j * small), (bx + cell, by + j * small), 2)

    grids = st.board["grids"]
    for b in range(9):
        base_x = (b % 3) * cell
        base_y = (b // 3) * cell
        for i in range(9):
            cx = i % 3
            cy = i // 3
            xpix = base_x + cx * small
            ypix = base_y + cy * small
            val = grids[b][i]
            if not val:
                continue
            if val == "X" and x_img:
                screen.blit(pygame.transform.smoothscale(x_img, (small, small)), (xpix, ypix))
            elif val == "O" and o_img:
                screen.blit(pygame.transform.smoothscale(o_img, (small, small)), (xpix, ypix))
            elif val == "Z" and z_img:
                screen.blit(pygame.transform.smoothscale(z_img, (small, small)), (xpix, ypix))
            else:
                t = font_small.render(val, True, COLOR_TEXT)
                screen.blit(t, t.get_rect(center=(xpix + small // 2, ypix + small // 2)))


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


# =========================================================
# MAIN
# =========================================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ultimate Noughts and Crosses")
    clock = pygame.time.Clock()

    # fonts
    font_title = pygame.font.SysFont("Segoe UI", 42, bold=True)
    font_sub = pygame.font.SysFont("Segoe UI", 26)
    font_body = pygame.font.SysFont("Segoe UI", 22)
    font_small = pygame.font.SysFont("Segoe UI", 18)

    # load images for actual game (optional)
    board_img = load_image("Images/board.png")
    x_img = load_image("Images/circlesquare.png")
    o_img = load_image("Images/oval.png")
    z_img = load_image("Images/tear.png")

    # UI state
    screen_mode = SCREEN_USERNAME
    username = ""
    ip_text = ""
    join_error = ""
    client_socket = None
    client_state = ClientState()
    host_local_ip = "127.0.0.1"

    running = True
    while running:
        # ------------------------------------------------
        # events
        # ------------------------------------------------
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            # USERNAME
            if screen_mode == SCREEN_USERNAME:
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN:
                        if username.strip():
                            screen_mode = SCREEN_MENU
                    elif e.key == pygame.K_BACKSPACE:
                        username = username[:-1]
                    else:
                        if e.unicode.isalnum() or e.unicode in ("_", "-"):
                            username += e.unicode

            # MAIN MENU
            elif screen_mode == SCREEN_MENU:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    if pygame.Rect(210, 260, 300, 60).collidepoint(mx, my):
                        screen_mode = SCREEN_HOST_CHOICE
                    elif pygame.Rect(210, 340, 300, 60).collidepoint(mx, my):
                        screen_mode = SCREEN_IP_INPUT
                        ip_text = ""
                        join_error = ""

            # HOST CHOICE
            elif screen_mode == SCREEN_HOST_CHOICE:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    # back
                    if pygame.Rect(30, 30, 90, 36).collidepoint(mx, my):
                        screen_mode = SCREEN_MENU
                    # 2 players
                    elif pygame.Rect(210, 240, 300, 60).collidepoint(mx, my):
                        start_server_in_thread(2)
                        client_state = ClientState()
                        try:
                            client_socket = connect_to_server("127.0.0.1", PORT, client_state, username)
                            host_local_ip = get_local_ip()
                            screen_mode = SCREEN_HOST_LOBBY
                        except OSError:
                            screen_mode = SCREEN_MENU
                    # 3 players
                    elif pygame.Rect(210, 320, 300, 60).collidepoint(mx, my):
                        start_server_in_thread(3)
                        client_state = ClientState()
                        try:
                            client_socket = connect_to_server("127.0.0.1", PORT, client_state, username)
                            host_local_ip = get_local_ip()
                            screen_mode = SCREEN_HOST_LOBBY
                        except OSError:
                            screen_mode = SCREEN_MENU

            # IP INPUT (JOIN)
            elif screen_mode == SCREEN_IP_INPUT:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    if pygame.Rect(30, 30, 90, 36).collidepoint(mx, my):
                        screen_mode = SCREEN_MENU
                        join_error = ""
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        screen_mode = SCREEN_MENU
                        join_error = ""
                    elif e.key == pygame.K_RETURN:
                        target = ip_text.strip()
                        if target:
                            client_state = ClientState()
                            try:
                                client_socket = connect_to_server(target, PORT, client_state, username)
                                screen_mode = SCREEN_GAME
                            except OSError:
                                join_error = "Could not connect. Check IP / same Wi-Fi."
                                ip_text = ""
                    elif e.key == pygame.K_BACKSPACE:
                        ip_text = ip_text[:-1]
                    else:
                        if e.unicode.isdigit() or e.unicode in (".", ":"):
                            ip_text += e.unicode

            # HOST LOBBY: no input needed right now

            # GAME SCREEN: clicks to place move
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

        # ------------------------------------------------
        # drawing
        # ------------------------------------------------
        if screen_mode == SCREEN_USERNAME:
            screen.fill(COLOR_BG)
            title = font_title.render("Enter username", True, COLOR_TEXT)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, 130)))

            input_rect = pygame.Rect(140, 230, 440, 56)
            draw_input(screen, input_rect, username, font_body, "your name")
            hint = font_small.render("Press Enter (cannot be empty)", True, COLOR_MUTED)
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 310)))

        elif screen_mode == SCREEN_MENU:
            screen.fill(COLOR_BG)
            # top bar
            pygame.draw.rect(screen, (15, 23, 42), (0, 0, WIDTH, 90))
            pygame.draw.line(screen, (30, 41, 59), (0, 90), (WIDTH, 90), 1)

            title = font_title.render("Ultimate Noughts and Crosses", True, COLOR_TEXT)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, 45)))

            hello = font_small.render(f"Hi {username}", True, COLOR_MUTED)
            screen.blit(hello, (20, 15))

            btn_host = pygame.Rect(210, 260, 300, 60)
            btn_join = pygame.Rect(210, 340, 300, 60)
            draw_button(screen, btn_host, "HOST A GAME", font_body, variant="primary")
            draw_button(screen, btn_join, "JOIN A GAME", font_body)

        elif screen_mode == SCREEN_HOST_CHOICE:
            screen.fill(COLOR_BG)
            # back
            back_rect = pygame.Rect(30, 30, 90, 36)
            draw_button(screen, back_rect, "Back", font_small)

            title = font_title.render("Host: choose players", True, COLOR_TEXT)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, 130)))

            draw_button(screen, pygame.Rect(210, 240, 300, 60), "2 PLAYERS", font_body, variant="primary")
            draw_button(screen, pygame.Rect(210, 320, 300, 60), "3 PLAYERS", font_body)

        elif screen_mode == SCREEN_IP_INPUT:
            screen.fill(COLOR_BG)

            back_rect = pygame.Rect(30, 30, 90, 36)
            draw_button(screen, back_rect, "Back", font_small)

            title = font_title.render("Join a game", True, COLOR_TEXT)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, 130)))

            input_rect = pygame.Rect(140, 230, 440, 56)
            draw_input(screen, input_rect, ip_text, font_body, "host IP (e.g. 10.0.0.5)")

            hint = font_small.render("Press Enter to join. Must be on same network.", True, COLOR_MUTED)
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 310)))

            if join_error:
                err = font_small.render(join_error, True, (248, 113, 113))
                screen.blit(err, err.get_rect(center=(WIDTH // 2, 350)))

        elif screen_mode == SCREEN_HOST_LOBBY:
            screen.fill(COLOR_BG)

            # header card
            pygame.draw.rect(screen, COLOR_PANEL, (80, 40, 560, 120), border_radius=18)
            h1 = font_sub.render("Hosting game", True, COLOR_TEXT)
            screen.blit(h1, (100, 60))
            ptxt = font_small.render("Give this IP to the other players:", True, COLOR_MUTED)
            screen.blit(ptxt, (100, 95))

            # IP card
            ip_rect = pygame.Rect(100, 130, 520, 46)
            pygame.draw.rect(screen, COLOR_INPUT_BG, ip_rect, border_radius=14)
            pygame.draw.rect(screen, COLOR_BORDER, ip_rect, 1, border_radius=14)
            ip_surf = font_body.render(host_local_ip, True, COLOR_TEXT)
            screen.blit(ip_surf, ip_surf.get_rect(center=ip_rect.center))

            # player status card
            pygame.draw.rect(screen, COLOR_PANEL, (80, 210, 560, 220), border_radius=18)
            status = font_body.render(
                f"Players: {client_state.connected_players}/{client_state.required_players}",
                True,
                COLOR_TEXT,
            )
            screen.blit(status, (110, 230))

            y = 270
            for mark in ("X", "O", "Z"):
                if mark in client_state.player_names:
                    line = font_small.render(f"{mark}: {client_state.player_names[mark]}", True, COLOR_TEXT)
                    screen.blit(line, (120, y))
                    y += 28

            # auto start when full
            if client_state.connected_players >= client_state.required_players:
                screen_mode = SCREEN_GAME

        elif screen_mode == SCREEN_GAME:
            draw_board(screen, client_state, board_img, x_img, o_img, z_img, font_small)
            # top bar
            pygame.draw.rect(screen, (15, 23, 42), (0, 0, WIDTH, 40))
            pygame.draw.line(screen, (30, 41, 59), (0, 40), (WIDTH, 40), 1)
            role = client_state.you_are or "?"
            your_name = client_state.player_names.get(role, "")
            label = f"You: {your_name} ({role})" if your_name else f"You: ({role})"
            info = f"{label}   |   Turn: {client_state.turn}   |   {client_state.connected_players}/{client_state.required_players}"
            surf = font_small.render(info, True, COLOR_TEXT)
            screen.blit(surf, (12, 10))

            if client_state.last_error:
                err = font_small.render(client_state.last_error, True, (248, 113, 113))
                screen.blit(err, (12, HEIGHT - 28))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
