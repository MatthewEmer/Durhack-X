import pygame


# Pygame Setup
pygame.init()

screen = pygame.display.set_mode((600, 600)) # Screen
screen.fill((255, 255, 255))

pygame.display.set_caption("Ultimate Tic-Tac-Toe") # Game Name

pygameIcon = pygame.image.load("Images/logo.png") # Logo
pygame.display.set_icon(pygameIcon)

pygame.display.flip()
#


# Graphics Resources
ovalIcon = pygame.image.load("Images/ovalThing.png")
tearIcon = pygame.image.load("Images/tearThing.png")
circleSquareIcon = pygame.image.load("Images/circleSquareThing.png")
board = pygame.image.load("Images/emptyBoard.png")

smallIcons = ["BLANK CELL", pygame.transform.scale(ovalIcon, (45, 45)), pygame.transform.scale(tearIcon, (45, 45)), pygame.transform.scale(circleSquareIcon, (45, 45))]
largeIcons = ["BLANK CELL", pygame.transform.scale(ovalIcon, (150, 150)), pygame.transform.scale(tearIcon, (150, 150)), pygame.transform.scale(circleSquareIcon, (150, 150))]

smallBoard = pygame.transform.scale(board, (170, 170))
largeBoard = pygame.transform.scale(board, (600, 600))

boardCovers = []
for i in range(9):
    boardCover = pygame.Surface((175, 175), pygame.SRCALPHA)
    boardCover.fill((0, 0, 0, 50))
    boardCovers.append(boardCover)
#


# Game Logic
class Board:
    def __init__(self, icon, x = 0, y = 0, cover=""):
        self.__icon = icon
        self.__x = x
        self.__y = y

        self.__cells = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.__filledCells = 0

        self.__covered = False
        self.__cover = cover

        self.__winner = 0

    
    # Getters and Setters
    def GetWinner(self):
        return self._Board__winner
    
    
    def SetWinner(self, playerNumber):
        self._Board__winner = playerNumber


    def GetCell(self, x, y):
        return self._Board__cells[(x % 3) + 3 * (y % 3)]
    

    def SetCell(self, x, y, player):
        if self._BoardGetCell(x, y) == 0:
            self._Board__cells[(x % 3) + 3 * (y % 3)] = player
            self._BoardCheckClear()
    #


    def Display(self):
        screen.blit(self._Board__icon, (self._Board__x, self._Board__y))


    def CheckForWin(self):
        return False


class Small_Board(Board):
    # Getters and Setters
    def SetCover(self, covered):
        self._Board__covered = covered
    #


    def Display(self, smallIcons, largeIcons):
        if self._Board__winner != 0:
            screen.blit(largeIcons[self._Board__winner], (self._Board__x + 10, self._Board__y + 10)) # Draws the large icon for a won board
            return
        
        screen.blit(self._Board__icon, (self._Board__x, self._Board__y)) # Draws the board

        cellShifts = [[2.8, 4.2], [62.5, 4.2], [122.2, 4.2], [2.8, 62.5], [62.5, 62.5], [122.2, 62.5], [2.8, 122.2], [62.5, 122.2], [122.2, 122.2]]
        for cellIndex in range(9):
            cellIcon = smallIcons[self._Board__cells[cellIndex]]

            if cellIcon == "BLANK CELL":
                continue

            screen.blit(cellIcon, (self._Board__x + cellShifts[cellIndex][0], self._Board__y + cellShifts[cellIndex][1])) # Draws the icons

        if self._Board__covered:
            screen.blit(self._Board__cover, (self._Board__x - 2.5, self._Board__y - 2))

        
    def CheckForClear(self):
        if self._Board__filledCells == 8:
            for cell in self._Board__cells:
                cell = 0
            self._Board__filledCells = 0
        else:
            self._Board__filledCells += 1

    
    def CheckForWin(self, x, y, player):
        if self._Board__filledCells < 3: 
            return
        
        if self._BoardGetCell(x + 1, y) == player and self._BoardGetCell(x - 1, y) == player: # Checks Row
            self._BoardSetWinner(player)
            return True
        elif self._BoardGetCell(x, y + 1) == player and self._BoardGetCell(x, y - 1) == player: # Checks Column
            self._BoardSetWinner(player)
            return True
        elif self._BoardGetCell(x + 1, y + 1) == player and self._BoardGetCell(x - 1, y - 1) == player: # Checks Diagonal 1
            self._BoardSetWinner(player)
            return True
        elif self._BoardGetCell(x - 1, y + 1) == player and self._BoardGetCell(x + 1, y - 1) == player: # Checks Diagonal 2
            self._BoardSetWinner(player)
            return True
        
        return False


class Big_Board(Board):
    def CheckForWin(self, x, y, player):
        if self._Board__filledCells < 2:
            return
        
        # Checks Rows
        if x != 2 and self._BoardGetCell(x + 1, y) == player:
            return True
        if x != 0 and self._BoardGetCell(x - 1, y) == player:
            return True
        #

        # Checks Columns
        if y != 2 and self._BoardGetCell(x, y + 1) == player:
            return True
        if y != 0 and self._BoardGetCell(x, y - 1) == player:
            return True
        #

        # Checks Diagonals 
        if x != 2 and y != 2 and self._BoardGetCell(x + 1, y + 1) == player:
            return True
        if x != 0 and y != 0 and self._BoardGetCell(x - 1, y - 1) == player:
            return True
        if x != 2 and y != 0 and self._BoardGetCell(x + 1, y - 1) == player:
            return True
        if x != 0 and y != 2 and self._BoardGetCell(x - 1, y + 1) == player:
            return True
        #
        
        return False
#


# Pygame Logic
def GetAction(keyPressEvent):
    if keyPressEvent.key == pygame.K_ESC:
        return "escape"
#


# Game Setup
mainBoard = Big_Board(largeBoard)

boardTL = Small_Board(smallBoard, 10, 15, boardCovers[0])
boardTM = Small_Board(smallBoard, 215, 15, boardCovers[1])
boardTR = Small_Board(smallBoard, 420, 15, boardCovers[2])

boardML = Small_Board(smallBoard, 10, 215, boardCovers[3])
boardMM = Small_Board(smallBoard, 215, 215, boardCovers[4])
boardMR = Small_Board(smallBoard, 420, 215, boardCovers[5])

boardBL = Small_Board(smallBoard, 10, 420, boardCovers[6])
boardBM = Small_Board(smallBoard, 215, 420, boardCovers[7])
boardBR = Small_Board(smallBoard, 420, 420, boardCovers[8])

boards = [boardTL, boardTM, boardTR, boardML, boardMM, boardMR, boardBL, boardBM, boardBR]
#


# Main Game Loop
gameOver = False
while not gameOver:
    # Graphics Placements
    mainBoard.Display()

    for board in boards:
        board.Display(smallIcons, largeIcons)
    #


    # Pygame Event Handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            gameOver = True
            
        if event.type == pygame.KEYDOWN:
            action = GetAction(event)

            if action == "escape":
                gameOver = True
    #

    pygame.display.flip() # Update the screen
#

pygame.quit()