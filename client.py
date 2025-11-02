import json
import socket
import threading
import pygame
import os
from typing import Optional, Dict, List, Tuple

from server import GameServer  # your updated server with 2-in-a-row big-board win


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
COLOR_BG = (15, 23, 42)          # slate-900
COLOR_PANEL = (30, 41, 59)       # slate-800
COLOR_PANEL_LIGHT = (51, 65, 85) # slate-700
COLOR_INPUT_BG = (15, 23, 42)
COLOR_BORDER = (71, 85, 105)
COLOR_TEXT = (248, 250, 252)
COLOR_MUTED = (148, 163, 184)
COLOR_ACCENT = (56, 189, 248)

# mapping server marks -> your icon indices
MARK_TO_ICON = {
    "O": 1,  # oval
    "Z": 2,  # tear
    "X": 3,  # circle-square
    None: 0,
    "": 0,
}

# button rects
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
# CLIENT STATE (FROM SERVER)
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
# === NEW UTTT LOGIC: image-based board classes
# =========================================================
class Board:
    def __init__(self, icon, x=0, y=0, cover=""):
        self.__icon = icon
        self.__x = x
        self.__y = y
        self.__cells = [0] * 9
        self.__filledCells = 0
        self.__covered = False
        self.__cover = cover
        self.__winner = 0
        self.__gameWinner = 0

    def GetWinner(self):
        return self._Board__winner

    def SetWinner(self, playerNumber):
        self._Board__winner = playerNumber

    def GetCell(self, x, y):
        return self._Board__cells[(x % 3) + 3 * (y % 3)]

    def SetCell(self, x, y, player):
        if Board.GetCell(self, x, y) == 0:
            self._Board__cells[(x % 3) + 3 * (y % 3)] = player

    def Display(self, screen):
        screen.blit(self._Board__icon, (self._Board__x, self._Board__y))


class Small_Board(Board):
    def GetCover(self):
        return self._Board__covered

    def SetCover(self, covered):
        self._Board__covered = covered

    def Display(self, screen, smallIcons, largeIcons):
        # draw big icon if board is won
        if self._Board__winner != 0:
            screen.blit(largeIcons[self._Board__winner], (self._Board__x + 10, self._Board__y + 10))
            return

        screen.blit(self._Board__icon, (self._Board__x, self._Board__y))
        cellShifts = [
            [2.8, 4.2], [62.5, 4.2], [122.2, 4.2],
            [2.8, 62.5], [62.5, 62.5], [122.2, 62.5],
            [2.8, 122.2], [62.5, 122.2], [122.2, 122.2]
        ]
        for i in range(9):
            cellIcon = self._Board__cells[i]
            if isinstance(cellIcon, int) and cellIcon != 0:
                icon_surf = smallIcons[cellIcon]
                if icon_surf != "BLANK CELL":
                    screen.blit(icon_surf, (self._Board__x + cellShifts[i][0], self._Board__y + cellShifts[i][1]))

        if self._Board__covered:
            screen.blit(self._Board__cover, (self._Board__x - 2.5, self._Board__y - 2))

    def DetectCellClick(self, x, y) -> int:
        if self._Board__winner != 0 or self.GetCover():
            return -1

        cellShifts = [
            [2.8, 4.2], [62.5, 4.2], [122.2, 4.2],
            [2.8, 62.5], [62.5, 62.5], [122.2, 62.5],
            [2.8, 122.2], [62.5, 122.2], [122.2, 122.2]
        ]
        cellSize = 45

        for i in range(9):
            cellX = self._Board__x + cellShifts[i][0]
            cellY = self._Board__y + cellShifts[i][1]
            if x >= cellX and x <= cellX + cellSize and y >= cellY and y <= cellY + cellSize:
                return i
        return -1


class Big_Board(Board):
    def GetGameWinner(self):
        return self._Board__gameWinner

    def SetGameWinner(self, player):
        self._Board__gameWinner = player

    def UpdateBoardWins(self, boards):
        for i in range(9):
            self.SetCell(i % 3, int(i / 3), boards[i].GetWinner())


def detect_board_from_pos(x, y) -> int:
    # same grid your original code used
    if x < 215:
        col = 0
    elif x < 420:
        col = 1
    else:
        col = 2

    if y < 215:
        row = 0
    elif y < 420:
        row = 1
    else:
        row = 2

    return row * 3 + col


def sync_from_server_to_boards(server_board: Dict, boards: List[Small_Board]):
    """Push server game state into our visual boards."""
    if not server_board:
        return

    grids = server_board.get("grids", [])
    next_forced = server_board.get("next_forced", None)
    big_wins = server_board.get("big_wins", [None] * 9)

    for b in range(9):
        sb = boards[b]
        cells = grids[b] if b < len(grids) else [None] * 9

        filled = 0
        for i in range(9):
            mark = cells[i]
            idx = MARK_TO_ICON.get(mark, 0)
            sb._Board__cells[i] = idx
            if idx != 0:
                filled += 1
        sb._Board__filledCells = filled

        # set winner if server says so
        if b < len(big_wins) and big_wins[b]:
            sb._Board__winner = MARK_TO_ICON.get(big_wins[b], 0)
        else:
            # don't force-clear; just leave it
            pass

    # cover logic
    if next_forced is not None and 0 <= next_forced < 9:
        for i in range(9):
            if i == next_forced:
                boards[i].SetCover(False)
            else:
                boards[i].SetCover(True)
    else:
        for i in range(9):
            boards[i].SetCover(False)
# =========================================================
# === END NEW UTTT LOGIC
# =========================================================


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ultimate Noughts and Crosses (Dark)")

    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("Segoe UI", 42, bold=True)
    font_body = pygame.font.SysFont("Segoe UI", 22)
    font_small = pygame.font.SysFont("Segoe UI", 18)

    # === NEW UTTT LOGIC: load images ===
    logo_img = load_image("Images/logo.png")
    if logo_img:
        pygame.display.set_icon(logo_img)

    ovalIcon = load_image("Images/ovalThing.png")
    tearIcon = load_image("Images/tearThing.png")
    circleSquareIcon = load_image("Images/circleSquareThing.png")
    board_img = load_image("Images/emptyBoard.png")

    smallIcons = [
        "BLANK CELL",
        pygame.transform.scale(ovalIcon, (45, 45)) if ovalIcon else "BLANK CELL",
        pygame.transform.scale(tearIcon, (45, 45)) if tearIcon else "BLANK CELL",
        pygame.transform.scale(circleSquareIcon, (45, 45)) if circleSquareIcon else "BLANK CELL",
    ]
    largeIcons = [
        "BLANK CELL",
        pygame.transform.scale(ovalIcon, (150, 150)) if ovalIcon else "BLANK CELL",
        pygame.transform.scale(tearIcon, (150, 150)) if tearIcon else "BLANK CELL",
        pygame.transform.scale(circleSquareIcon, (150, 150)) if circleSquareIcon else "BLANK CELL",
    ]
    smallBoardImg = pygame.transform.scale(board_img, (170, 170)) if board_img else None
    largeBoardImg = pygame.transform.scale(board_img, (600, 600)) if board_img else None

    boardCovers = []
    for _ in range(9):
        cover = pygame.Surface((175, 175), pygame.SRCALPHA)
        cover.fill((0, 0, 0, 50))
        boardCovers.append(cover)

    # make 9 boards in positions (same as original)
    mainBoard = Big_Board(largeBoardImg if largeBoardImg else pygame.Surface((600, 600)))
    boardTL = Small_Board(smallBoardImg, 10, 15, boardCovers[0])
    boardTM = Small_Board(smallBoardImg, 215, 15, boardCovers[1])
    boardTR = Small_Board(smallBoardImg, 420, 15, boardCovers[2])

    boardML = Small_Board(smallBoardImg, 10, 215, boardCovers[3])
    boardMM = Small_Board(smallBoardImg, 215, 215, boardCovers[4])
    boardMR = Small_Board(smallBoardImg, 420, 215, boardCovers[5])

    boardBL = Small_Board(smallBoardImg, 10, 420, boardCovers[6])
    boardBM = Small_Board(smallBoardImg, 215, 420, boardCovers[7])
    boardBR = Small_Board(smallBoardImg, 420, 420, boardCovers[8])

    uttt_boards = [
        boardTL, boardTM, boardTR,
        boardML, boardMM, boardMR,
        boardBL, boardBM, boardBR
    ]
    # === END NEW UTTT LOGIC

    # runtime state
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

            # GAME (online) -- handle clicks
            elif screen_mode == SCREEN_GAME:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = e.pos
                    # === NEW UTTT LOGIC: click -> (big, small) -> send
                    if 0 <= mx <= 620 and 0 <= my <= 620:
                        b_idx = detect_board_from_pos(mx, my)
                        if 0 <= b_idx < 9:
                            cell_idx = uttt_boards[b_idx].DetectCellClick(mx, my)
                            if cell_idx != -1 and client_socket and client_state.board:
                                send(client_socket, {
                                    "type": "move",
                                    "big": b_idx,
                                    "small": cell_idx
                                })
                    # === END NEW UTTT LOGIC

        # =====================================================
        # DRAW
        # =====================================================
        if screen_mode == SCREEN_USERNAME:
            screen.fill(COLOR_BG)
            title = font_title.render("Enter username", True, COLOR_TEXT)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, 140)))
            input_rect = pygame.Rect(140, 240, 440, 56)
            draw_input(screen, input_rect, username, font_body, "your name")
            hint = font_small.render("Press Enter (cannot be empty)", True, COLOR_MUTED)
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 320)))

        elif screen_mode == SCREEN_MENU:
            screen.fill(COLOR_BG)
            title = font_title.render("Ultimate Noughts and Crosses", True, COLOR_TEXT)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, 110)))
            hello = font_small.render(f"Hi {username}", True, COLOR_MUTED)
            screen.blit(hello, (20, 20))
            draw_button(screen, BTN_MENU_HOST, "HOST A GAME", font_body, variant="primary")
            draw_button(screen, BTN_MENU_JOIN, "JOIN A GAME", font_body)

        elif screen_mode == SCREEN_HOST_CHOICE:
            screen.fill(COLOR_BG)
            draw_button(screen, BTN_BACK, "Back", font_small)
            title = font_title.render("Host: choose players", True, COLOR_TEXT)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, 130)))
            draw_button(screen, BTN_HOST_2, "2 PLAYERS", font_body, variant="primary")
            draw_button(screen, BTN_HOST_3, "3 PLAYERS", font_body)

        elif screen_mode == SCREEN_IP_INPUT:
            screen.fill(COLOR_BG)
            draw_button(screen, BTN_BACK, "Back", font_small)
            title = font_title.render("Join a game", True, COLOR_TEXT)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, 130)))
            input_rect = pygame.Rect(140, 230, 440, 56)
            draw_input(screen, input_rect, ip_text, font_body, "host IP (e.g. 10.0.0.5)")
            if join_error:
                err = font_small.render(join_error, True, (248, 113, 113))
                screen.blit(err, err.get_rect(center=(WIDTH // 2, 320)))

        elif screen_mode == SCREEN_HOST_LOBBY:
            screen.fill(COLOR_BG)
            # header card
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

            # player list
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

            # auto-start
            if client_state.connected_players >= client_state.required_players:
                screen_mode = SCREEN_GAME

        elif screen_mode == SCREEN_GAME:
            # draw dark background
            screen.fill(COLOR_BG)

            # sync remote state into local boards
            sync_from_server_to_boards(client_state.board, uttt_boards)

            # draw main big board area
            # center it a bit – but your board is 600x600, so we can just put at (60,50)
            if mainBoard._Board__icon:
                screen.blit(mainBoard._Board__icon, (60, 50))
            else:
                pygame.draw.rect(screen, (19, 28, 45), (60, 50, 600, 600), border_radius=20)

            # draw 9 small boards
            # but they were positioned for (0,0) so we shift temporarily? to keep it simple, we keep (0,0) style
            # you placed them at 10/215/420 etc so we can just blit with +50 offset
            offset_x = 60 - 0
            offset_y = 50 - 0
            for i, b in enumerate(uttt_boards):
                # we need to temporarily move board to offset for drawing, then restore
                old_x = b._Board__x
                old_y = b._Board__y
                b._Board__x = old_x + offset_x
                b._Board__y = old_y + offset_y
                b.Display(screen, smallIcons, largeIcons)
                b._Board__x = old_x
                b._Board__y = old_y

            # HUD
            pygame.draw.rect(screen, COLOR_BG, (0, 0, WIDTH, 40))
            hud_txt = f"Turn: {client_state.turn}  |  Players: {client_state.connected_players}/{client_state.required_players}"
            if client_state.you_are:
                pname = client_state.player_names.get(client_state.you_are, "")
                hud_txt = f"You: {pname} ({client_state.you_are})  |  {hud_txt}"
            hud_surf = font_small.render(hud_txt, True, COLOR_TEXT)
            screen.blit(hud_surf, (15, 10))

            # server might send big_winner (when 2-in-a-row)
            if client_state.board and client_state.board.get("big_winner"):
                win_txt = f"Winner: {client_state.board['big_winner']}"
                win_surf = font_title.render(win_txt, True, (248, 113, 113))
                screen.blit(win_surf, win_surf.get_rect(center=(WIDTH // 2, 680)))

            if client_state.last_error:
                err = font_small.render(client_state.last_error, True, (248, 113, 113))
                screen.blit(err, (15, HEIGHT - 28))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
