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
pieceIcons = [pygame.image.load("Images/ovalThing.png"), pygame.image.load("Images/tearThing.png"), pygame.image.load("Images/circleSquareThing.png")]

board = pygame.image.load("Images/emptyBoard.png")
smallBoard = pygame.transform.scale(board, (170, 170))
largeBoard = pygame.transform.scale(board, (600, 600))
#


# Main Game Loop
gameOver = False
while (not gameOver):
    # Graphics Placements
    screen.blit(largeBoard, (0, 0))

    screen.blit(smallBoard, (10, 15)) # Top-Left
    screen.blit(smallBoard, (215, 15)) # Top-Middle
    screen.blit(smallBoard, (420, 15)) # Top-Right

    screen.blit(smallBoard, (10, 215)) # Middle-Left
    screen.blit(smallBoard, (215, 215)) # Middle-Middle
    screen.blit(smallBoard, (420, 215)) # Middle-Right

    screen.blit(smallBoard, (10, 420)) # Bottom-Left
    screen.blit(smallBoard, (215, 420)) # Bottom-Middle
    screen.blit(smallBoard, (420, 420)) # Bottom-Right
    #


    # Pygame Event Handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            gameOver = True
    #

    pygame.display.flip() # Update the screen
#

pygame.quit()