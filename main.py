import pygame

pygame.init()

SCREEN_DIMENSIONS = (600, 600)


# Pygame Variables
screen = pygame.display.set_mode(SCREEN_DIMENSIONS)
pygame.display.set_caption("Ultimate Tic-Tac-Toe")
#


# Main Game Loop
gameOver = False
while (not gameOver):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            gameOver = True
#

pygame.quit()