import pygame
import sys
from src.game import Game


def main():
    pygame.init()
    pygame.font.init()
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
