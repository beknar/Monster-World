#!/usr/bin/env python3
"""2D Action RPG - Main entry point."""

import pygame
from src.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
