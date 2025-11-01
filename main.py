import pygame

SCREEN_DIMENSIONS = (600, 600)


# Pygame Setup
pygame.init()

screen = pygame.display.set_mode(SCREEN_DIMENSIONS) # Screen

pygame.display.set_caption("Ultimate Tic-Tac-Toe") # Game Name

pygameIcon = pygame.image.load("Images/logo.png") # Logo
pygame.display.set_icon(pygameIcon)

screen.fill((255, 255, 255))
pygame.display.flip()
#


# Graphics Resources
pieceIcons = ["BLANK CELL", pygame.image.load("Images/ovalThing.png"), pygame.image.load("Images/tearThing.png"), pygame.image.load("Images/circleSquareThing.png")]

board = pygame.image.load("Images/emptyBoard.png")
smallBoard = pygame.transform.scale(board, (170, 170))
largeBoard = pygame.transform.scale(board, (600, 600))
#


# Game Logic
class Small_Board:
    def __init__(self, icon, x, y):
        self.icon = icon
        self.cells = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.x = x
        self.y = y

    def Display(self):
        screen.blit(self.icon, (self.x, self.y))
#


# Game Setup
boardTL = Small_Board(smallBoard, 10, 15)
boardTM = Small_Board(smallBoard, 215, 15)
boardTR = Small_Board(smallBoard, 420, 15)

boardML = Small_Board(smallBoard, 10, 215)
boardMM = Small_Board(smallBoard, 215, 215)
boardMR = Small_Board(smallBoard, 420, 215)

boardBL = Small_Board(smallBoard, 10, 420)
boardBM = Small_Board(smallBoard, 215, 420)
boardBR = Small_Board(smallBoard, 420, 420)

boards = [boardTL, boardTM, boardTR, boardML, boardMM, boardMR, boardBL, boardBM, boardBR]
#


# Main Game Loop
gameOver = False
while (not gameOver):
    # Graphics Placements
    screen.blit(largeBoard, (0, 0))

    for board in boards:
        board.Display()
    #


    # Pygame Event Handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            gameOver = True
    #

    pygame.display.flip() # Update the screen
#

pygame.quit()