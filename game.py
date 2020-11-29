#!/usr/bin/env python3

from game_tools.classes import *


def start_game():
    game = Game()
    game.play()


if __name__ == '__main__':
    try:
        start_game()
    except KeyboardInterrupt:
        answ = input("Try again [N]o/yes: ")
        if re.search(r'[Yy](es)*', answ):
            start_game()