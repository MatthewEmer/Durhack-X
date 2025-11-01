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
class Small_Board:
    def __init__(self, icon, cover, x, y):
        self.icon = icon
        self.cells = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.x = x
        self.y = y

        self.finished = False
        self.winner = 0

        self.covered = False
        self.cover = cover


    def Display(self, smallIcons, largeIcons):
        if self.finished:
            screen.blit(largeIcons[self.winner], (self.x + 10, self.y + 10)) # Draws the large icon for a won board
            return
        
        screen.blit(self.icon, (self.x, self.y)) # Draws the board

        cellShifts = [[2.8, 4.2], [62.5, 4.2], [122.2, 4.2], [2.8, 62.5], [62.5, 62.5], [122.2, 62.5], [2.8, 122.2], [62.5, 122.2], [122.2, 122.2]]
        for cellIndex in range(9):
            cellIcon = smallIcons[self.cells[cellIndex]]

            if cellIcon == "BLANK CELL":
                continue

            screen.blit(cellIcon, (self.x + cellShifts[cellIndex][0], self.y + cellShifts[cellIndex][1])) # Draws the icons

        if self.covered:
            screen.blit(self.cover, (self.x - 2.5, self.y - 2))

    
    def SetWinner(self, playerNumber):
        self.finished = True
        self.winner = playerNumber


    def SetCover(self, covered):
        self.covered = covered
#


# Game Setup
boardTL = Small_Board(smallBoard, boardCovers[0], 10, 15)
boardTM = Small_Board(smallBoard, boardCovers[1], 215, 15)
boardTR = Small_Board(smallBoard, boardCovers[2], 420, 15)

boardML = Small_Board(smallBoard, boardCovers[3], 10, 215)
boardMM = Small_Board(smallBoard, boardCovers[4], 215, 215)
boardMR = Small_Board(smallBoard, boardCovers[5], 420, 215)

boardBL = Small_Board(smallBoard, boardCovers[6], 10, 420)
boardBM = Small_Board(smallBoard, boardCovers[7], 215, 420)
boardBR = Small_Board(smallBoard, boardCovers[8], 420, 420)

boards = [boardTL, boardTM, boardTR, boardML, boardMM, boardMR, boardBL, boardBM, boardBR]
#


# Main Game Loop
gameOver = False
while (not gameOver):
    # Graphics Placements
    screen.blit(largeBoard, (0, 0))

    for board in boards:
        board.Display(smallIcons, largeIcons)
    #


    # Pygame Event Handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            gameOver = True
    #

    pygame.display.flip() # Update the screen
#

pygame.quit()