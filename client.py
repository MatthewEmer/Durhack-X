import json
import socket
import threading
import pygame
import os
from typing import Optional, Dict, List

# we import server so we can start it locally when we pick “host”
from server import GameServer   # <-- your server.py with 2-in-a-row


# =========================================================
# CONFIG
# =========================================================
WIDTH, HEIGHT = 720, 720
PORT = 8765

# screens
SCREEN_USERNAME = "username"
SCREEN_MENU = "menu"
SCREEN_HOST_CHOICE = "host_choice"
SCREEN_IP_INPUT = "ip_input"
SCREEN_HOST_LOBBY = "host_lobby"
SCREEN_GAME = "game"

# DARK PALETTE
COLOR_BG = (15, 23, 42)
COLOR_PANEL = (30, 41, 59)
COLOR_PANEL_LIGHT = (51, 65, 85)
COLOR_INPUT_BG = (15, 23, 42)
COLOR_BORDER = (71, 85, 105)
COLOR_TEXT = (248, 250, 252)
COLOR_MUTED = (148, 163, 184)
COLOR_ACCENT = (56, 189, 248)
COLOR_RED = (248, 113, 113)

BTN_MENU_HOST = pygame.Rect(210, 260, 300, 56)
BTN_MENU_JOIN = pygame.Rect(210, 330, 300, 56)
BTN_BACK = pygame.Rect(30, 30, 90, 36)
BTN_HOST_2 = pygame.Rect(210, 240, 300, 56)
BTN_HOST_3 = pygame.Rect(210, 310, 300, 56)


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
                on_msg(json.loads(buf.decode("utf-8")))
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
    try:
        tmp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tmp.connect(("8.8.8.8", 80))
        ip = tmp.getsockname()[0]
        tmp.close()
        return ip
    except OSError:
        return "127.0.0.1"


# =========================================================
# CLIENT STATE
# =========================================================
class ClientState:
    def __init__(self):
        self.you_are: Optional[str] = None
        self.turn: str = "X"
        self.board = None
        self.required_players: int = 2
        self.connected_players: int = 0
        self.player_names: Dict[str, str] = {}
        self.spectator_names: List[str] = []
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
# === NEW UTTT LOGIC (image-based, aligned) ================
# =========================================================
# We now ALLOW for 2 input sets:
# - your images in /Images (board.png, oval.png, tear.png, circlesquare.png)
# - OR fallback to plain draw if any is missing


class SmallBoard:
    # drawn at self.x, self.y (we will use exactly your original coords)
    def __init__(self, x, y, board_img=None, cover_surf=None,
                 oval=None, tear=None, cs=None):
        self.x = x
        self.y = y
        self.w = 170
        self.h = 170
        self.cells: List[Optional[str]] = [None] * 9
        self.covered = False
        self.winner: Optional[str] = None

        # images (can be None)
        self.board_img = board_img
        self.cover_surf = cover_surf
        self.oval = oval
        self.tear = tear
        self.cs = cs

    def display(self, screen, font_cell):
        # draw board base
        if self.board_img:
            screen.blit(self.board_img, (self.x, self.y))
        else:
            pygame.draw.rect(screen, (19, 28, 45), (self.x, self.y, self.w, self.h), border_radius=10)
            # simple inner grid
            for i in range(1, 3):
                pygame.draw.line(screen, COLOR_BORDER,
                                 (self.x + i * (self.w // 3), self.y),
                                 (self.x + i * (self.w // 3), self.y + self.h), 2)
                pygame.draw.line(screen, COLOR_BORDER,
                                 (self.x, self.y + i * (self.h // 3)),
                                 (self.x + self.w, self.y + i * (self.h // 3)), 2)

        # if small board is already won -> draw big symbol
        if self.winner:
            # draw big centered text or image
            if self.winner == "O" and self.oval:
                big = pygame.transform.smoothscale(self.oval, (150, 150))
                screen.blit(big, (self.x + 10, self.y + 10))
            elif self.winner == "Z" and self.tear:
                big = pygame.transform.smoothscale(self.tear, (150, 150))
                screen.blit(big, (self.x + 10, self.y + 10))
            elif self.winner == "X" and self.cs:
                big = pygame.transform.smoothscale(self.cs, (150, 150))
                screen.blit(big, (self.x + 10, self.y + 10))
            else:
                t = font_cell.render(self.winner, True, COLOR_TEXT)
                screen.blit(t, t.get_rect(center=(self.x + self.w // 2, self.y + self.h // 2)))
            return

        # draw 9 cells
        cell_positions = [
            (2.8, 4.2), (62.5, 4.2), (122.2, 4.2),
            (2.8, 62.5), (62.5, 62.5), (122.2, 62.5),
            (2.8, 122.2), (62.5, 122.2), (122.2, 122.2)
        ]
        for i, mark in enumerate(self.cells):
            if not mark:
                continue
            cx, cy = cell_positions[i]
            if mark == "O" and self.oval:
                img = pygame.transform.smoothscale(self.oval, (45, 45))
                screen.blit(img, (self.x + cx, self.y + cy))
            elif mark == "Z" and self.tear:
                img = pygame.transform.smoothscale(self.tear, (45, 45))
                screen.blit(img, (self.x + cx, self.y + cy))
            elif mark == "X" and self.cs:
                img = pygame.transform.smoothscale(self.cs, (45, 45))
                screen.blit(img, (self.x + cx, self.y + cy))
            else:
                # text fallback
                t = font_cell.render(mark, True, COLOR_TEXT)
                rect = t.get_rect(center=(self.x + cx + 22, self.y + cy + 22))
                screen.blit(t, rect)

        # cover
        if self.covered and self.cover_surf:
            screen.blit(self.cover_surf, (self.x - 2, self.y - 2))
        elif self.covered:
            cover = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            cover.fill((0, 0, 0, 90))
            screen.blit(cover, (self.x, self.y))

    def detect_click(self, mx, my) -> int:
        """Return small cell index 0..8 OR -1 if not inside/covered/won."""
        if self.winner or self.covered:
            return -1
        if not (self.x <= mx <= self.x + self.w and self.y <= my <= self.y + self.h):
            return -1

        # these are EXACTLY the numbers you had in your original local script
        cell_positions = [
            (2.8, 4.2), (62.5, 4.2), (122.2, 4.2),
            (2.8, 62.5), (62.5, 62.5), (122.2, 62.5),
            (2.8, 122.2), (62.5, 122.2), (122.2, 122.2)
        ]
        cell_size = 45

        for i, (cx, cy) in enumerate(cell_positions):
            sx = self.x + cx
            sy = self.y + cy
            if sx <= mx <= sx + cell_size and sy <= my <= sy + cell_size:
                return i
        return -1


def make_image_boards():
    # try to load your images
    board_img = load_image("Images/board.png")
    oval_img = load_image("Images/oval.png")
    tear_img = load_image("Images/tear.png")
    cs_img = load_image("Images/circlesquare.png")

    # make covers
    board_covers = []
    for _ in range(9):
        cov = pygame.Surface((175, 175), pygame.SRCALPHA)
        cov.fill((0, 0, 0, 50))
        board_covers.append(cov)

    # IMPORTANT: use your ORIGINAL positions so clicks line up
    boards = [
        SmallBoard(10, 15,  board_img, board_covers[0], oval_img, tear_img, cs_img),
        SmallBoard(215, 15, board_img, board_covers[1], oval_img, tear_img, cs_img),
        SmallBoard(420, 15, board_img, board_covers[2], oval_img, tear_img, cs_img),
        SmallBoard(10, 215, board_img, board_covers[3], oval_img, tear_img, cs_img),
        SmallBoard(215, 215, board_img, board_covers[4], oval_img, tear_img, cs_img),
        SmallBoard(420, 215, board_img, board_covers[5], oval_img, tear_img, cs_img),
        SmallBoard(10, 420, board_img, board_covers[6], oval_img, tear_img, cs_img),
        SmallBoard(215, 420, board_img, board_covers[7], oval_img, tear_img, cs_img),
        SmallBoard(420, 420, board_img, board_covers[8], oval_img, tear_img, cs_img),
    ]
    return boards


def sync_from_server_to_boards(server_board: Dict, boards: List[SmallBoard]):
    """Take server board (grids, next_forced, big_wins) and push into our objects."""
    if not server_board:
        return

    grids = server_board.get("grids", [])
    next_forced = server_board.get("next_forced", None)
    big_wins = server_board.get("big_wins", [None] * 9)

    for i in range(9):
        sb = boards[i]
        sb.cells = grids[i][:] if i < len(grids) else [None] * 9
        sb.winner = big_wins[i] if i < len(big_wins) else None

    # cover logic (forced board)
    if next_forced is not None and 0 <= next_forced < 9:
        for i in range(9):
            boards[i].covered = (i != next_forced)
    else:
        for i in range(9):
            boards[i].covered = False
# =========================================================
# === END UTTT LOGIC ======================================
# =========================================================


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ultimate Noughts and Crosses (dark + images)")

    clock = pygame.time.Clock()

    # fonts
    font_title = pygame.font.SysFont("Segoe UI", 42, bold=True)
    font_body = pygame.font.SysFont("Segoe UI", 22)
    font_small = pygame.font.SysFont("Segoe UI", 16)
    font_cell = pygame.font.SysFont("Segoe UI", 28, bold=True)

    # menu backgrounds (optional)
    bg_username = load_image("Images/username.png")
    bg_mainmenu = load_image("Images/mainmenu.png")
    bg_hostchoice = load_image("Images/hostchoice.png")
    bg_enterip = load_image("Images/enterip.png")
    bg_hostlobby = load_image("Images/hostlobby.png")
    logo = load_image("Images/logo.png")
    if logo:
        pygame.display.set_icon(logo)

    # 9 game boards
    uttt_boards = make_image_boards()

    # runtime
    screen_mode = SCREEN_USERNAME
    username = ""
    ip_text = ""
    join_error = ""
    client_state = ClientState()
    client_socket = None
    host_local_ip = "127.0.0.1"

    running = True
    while running:
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

            # MENU
            elif screen_mode == SCREEN_MENU:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    if BTN_MENU_HOST.collidepoint(mx, my):
                        screen_mode = SCREEN_HOST_CHOICE
                    elif BTN_MENU_JOIN.collidepoint(mx, my):
                        screen_mode = SCREEN_IP_INPUT
                        ip_text = ""
                        join_error = ""

            # HOST CHOICE
            elif screen_mode == SCREEN_HOST_CHOICE:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    if BTN_BACK.collidepoint(mx, my):
                        screen_mode = SCREEN_MENU
                    elif BTN_HOST_2.collidepoint(mx, my):
                        start_server_in_thread(2)
                        client_state = ClientState()
                        try:
                            client_socket = connect_to_server("127.0.0.1", PORT, client_state, username)
                            host_local_ip = get_local_ip()
                            screen_mode = SCREEN_HOST_LOBBY
                        except OSError:
                            screen_mode = SCREEN_MENU
                    elif BTN_HOST_3.collidepoint(mx, my):
                        start_server_in_thread(3)
                        client_state = ClientState()
                        try:
                            client_socket = connect_to_server("127.0.0.1", PORT, client_state, username)
                            host_local_ip = get_local_ip()
                            screen_mode = SCREEN_HOST_LOBBY
                        except OSError:
                            screen_mode = SCREEN_MENU

            # IP INPUT
            elif screen_mode == SCREEN_IP_INPUT:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    if BTN_BACK.collidepoint(mx, my):
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

            # GAME
            elif screen_mode == SCREEN_GAME:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    # IMPORTANT: no offset now, we use exact board coords
                    for idx, sb in enumerate(uttt_boards):
                        cell_idx = sb.detect_click(mx, my)
                        if cell_idx != -1:
                            if client_socket and client_state.board:
                                send(client_socket, {
                                    "type": "move",
                                    "big": idx,
                                    "small": cell_idx
                                })
                            break

        # =================================================
        # DRAW
        # =================================================
        if screen_mode == SCREEN_USERNAME:
            if bg_username:
                screen.blit(bg_username, (0, 0))
            else:
                screen.fill(COLOR_BG)
            title = font_title.render("Enter username", True, COLOR_TEXT)
            screen.blit(title, (60, 90))
            input_rect = pygame.Rect(140, 240, 440, 56)
            draw_input(screen, input_rect, username, font_body, "your name")
            hint = font_small.render("Press Enter (cannot be empty)", True, COLOR_MUTED)
            screen.blit(hint, (160, 310))

        elif screen_mode == SCREEN_MENU:
            if bg_mainmenu:
                screen.blit(bg_mainmenu, (0, 0))
            else:
                screen.fill(COLOR_BG)
            title = font_title.render("Ultimate Noughts and Crosses", True, COLOR_TEXT)
            screen.blit(title, (60, 90))
            hello = font_small.render(f"Hi {username}", True, COLOR_MUTED)
            screen.blit(hello, (20, 20))
            draw_button(screen, BTN_MENU_HOST, "HOST A GAME", font_body, variant="primary")
            draw_button(screen, BTN_MENU_JOIN, "JOIN A GAME", font_body)

        elif screen_mode == SCREEN_HOST_CHOICE:
            if bg_hostchoice:
                screen.blit(bg_hostchoice, (0, 0))
            else:
                screen.fill(COLOR_BG)
            draw_button(screen, BTN_BACK, "Back", font_small)
            title = font_title.render("Host: choose players", True, COLOR_TEXT)
            screen.blit(title, (60, 100))
            draw_button(screen, BTN_HOST_2, "2 PLAYERS", font_body, variant="primary")
            draw_button(screen, BTN_HOST_3, "3 PLAYERS", font_body)

        elif screen_mode == SCREEN_IP_INPUT:
            if bg_enterip:
                screen.blit(bg_enterip, (0, 0))
            else:
                screen.fill(COLOR_BG)
            draw_button(screen, BTN_BACK, "Back", font_small)
            title = font_title.render("Join a game", True, COLOR_TEXT)
            screen.blit(title, (60, 100))
            input_rect = pygame.Rect(140, 230, 440, 56)
            draw_input(screen, input_rect, ip_text, font_body, "host IP (e.g. 10.0.0.5)")
            if join_error:
                err = font_small.render(join_error, True, COLOR_RED)
                screen.blit(err, (140, 300))

        elif screen_mode == SCREEN_HOST_LOBBY:
            if bg_hostlobby:
                screen.blit(bg_hostlobby, (0, 0))
            else:
                screen.fill(COLOR_BG)

            pygame.draw.rect(screen, COLOR_PANEL, (80, 40, 560, 120), border_radius=18)
            h1 = font_body.render("Hosting game", True, COLOR_TEXT)
            screen.blit(h1, (100, 60))
            ptxt = font_small.render("Give this IP to other players:", True, COLOR_MUTED)
            screen.blit(ptxt, (100, 90))

            ip_rect = pygame.Rect(100, 130, 520, 46)
            pygame.draw.rect(screen, COLOR_INPUT_BG, ip_rect, border_radius=14)
            pygame.draw.rect(screen, COLOR_BORDER, ip_rect, 1, border_radius=14)
            ip_surf = font_body.render(host_local_ip, True, COLOR_TEXT)
            screen.blit(ip_surf, ip_surf.get_rect(center=ip_rect.center))

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
                    y += 26

            if client_state.connected_players >= client_state.required_players:
                screen_mode = SCREEN_GAME

        elif screen_mode == SCREEN_GAME:
            # **important**: no background image here, we want clear board
            screen.fill(COLOR_BG)

            # sync server -> local boards
            sync_from_server_to_boards(client_state.board, uttt_boards)

            # draw all 9 boards at EXACT coords (10,15 etc.) — so clicks match!
            for i, sb in enumerate(uttt_boards):
                forced = False
                if client_state.board and client_state.board.get("next_forced") is not None:
                    forced = (i == client_state.board["next_forced"])
                # we don't actually need "forced" here because the board itself already has covered=True
                sb.display(screen, font_cell)

            # HUD
            hud_txt = f"Turn: {client_state.turn}  |  Players: {client_state.connected_players}/{client_state.required_players}"
            if client_state.you_are:
                pname = client_state.player_names.get(client_state.you_are, "")
                hud_txt = f"You: {pname} ({client_state.you_are})  |  {hud_txt}"
            hud_surf = font_small.render(hud_txt, True, COLOR_TEXT)
            screen.blit(hud_surf, (12, 8))

            # big winner (server-side 2-in-a-row)
            if client_state.board and client_state.board.get("big_winner"):
                win_txt = f"Winner: {client_state.board['big_winner']}"
                win_surf = font_title.render(win_txt, True, COLOR_RED)
                screen.blit(win_surf, win_surf.get_rect(center=(WIDTH // 2, 690)))

            if client_state.last_error:
                err_surf = font_small.render(client_state.last_error, True, COLOR_RED)
                screen.blit(err_surf, (12, HEIGHT - 28))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
