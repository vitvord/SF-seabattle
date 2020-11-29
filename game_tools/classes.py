import logging
import re
import random
from functools import reduce
from time import time
from time import sleep
from os import system
import sys
from copy import deepcopy
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG = logging.getLogger('battle')


class Player:
    def __init__(self, field, name='Krang', robot=True):
        self.name = name
        self.playground = field
        self.robot = robot

    def init_player(self):
        self.name = input("Enter the name for Player 1: ")
        self.playground.init_ships()

    def __str__(self):
        return self.name


class Brain(Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.steps = []
        self.hits = []
        self.to_shot = []

    def get_random_cell(self, available_cells):
        step = random.choice(list(available_cells))
        self.steps.append(step)
        return step

    def get_neighbors_cells(self, field, coord):
        x, y = coord
        neighbors = {(x, y-1), (x, y+1), (x-1, y), (x+1, y)}
        return field._playable_cells & neighbors - set(self.steps)

    def shot_next(self, field):
        if self.to_shot:
            shot_coord_x, shot_coord_y = self.to_shot.pop()
        else:
            shot_coord_x, shot_coord_y = self.get_random_cell(field._playable_cells)
        LOG.debug(f"Shot to coord: {shot_coord_x}, {shot_coord_y}")
        shot_result = field.shot(shot_coord_x, shot_coord_y)
        if shot_result == -1:
            self.to_shot = []
            self.hits = []
        elif shot_result:
            self.hits.append((shot_coord_x, shot_coord_y))
            if len(self.hits) == 1:
                self.to_shot = sorted(self.get_neighbors_cells(field, self.steps[-1]))
            if len(self.hits) > 1:
                self.to_shot = sorted(self._get_ends(self.hits, field))
        self.steps.append((shot_coord_x, shot_coord_y))
        return shot_result

    @staticmethod
    def _get_ends(hits, field):
        # vertical ship
        if hits[0][0] == hits[1][0]:
            return field._playable_cells & {(hits[0][0], hits[0][1] - 1), (hits[0][0], hits[-1][1] + 1)}
        # horizontal ship
        elif hits[0][1] == hits[1][1]:
            return field._playable_cells & {(hits[0][0] - 1, hits[0][1]), (hits[-1][0] + 1, hits[0][1])}
        else:
            raise ValueError("Something wrong with ships to shot")


class Ship:
    def __init__(self, start_pos: tuple, horizontal: bool = True, length: int = 1):
        self.coord = self._init_ship(start_pos, horizontal, length)
        self.length = length
        self.life = length

    @staticmethod
    def _init_ship(start: tuple, hz: bool, l: int) -> frozenset:
        if hz:
            return frozenset((start[0] + x, start[1]) for x in range(l))
        return frozenset((start[0], start[1] + y) for y in range(l))

    def check_my_coord(self, x, y):
        return (x, y) in self.coord

    def check_shot(self, x, y):
        if self.check_my_coord(x, y):
            self.life -= 1
            return True
        return False

    def __repr__(self):
        return f"{self.coord} life: {self.life}, length: {self.length}"


class Field:
    field_cell_map = {
        'empty': 'O',
        'miss': 'T',
        'dead': 'X',
        'hit': 'x',
        'occupied': '-',
        'ship': '+',
    }
    # length: count
    available_ships = {
        1: 4,
        2: 2,
        3: 1,
    }

    def __init__(self, size: int, ships: list = None):
        self.field_size = size
        self.steps = set()
        self.ships = ships if ships else []
        self.__field = [[self.field_cell_map['empty']] * size for _ in range(size)]
        self._playable_cells = {(x, y) for x in range(size) for y in range(size)}
        self.revert_coord = set()

    def init_ships(self):
        rand_ships_answ = input("Try to use random ships? [N]o/yes: ")
        if re.search(r'[Yy](es)?', rand_ships_answ):
            return self.place_random_ships()
        ship_for_place = self.available_ships.copy()
        for ship_len in sorted(reduce(lambda s, x: s + [x[0]] * x[1], ship_for_place.items(), []),
                               reverse=True):
            self.print_field(hide=False)
            print(f"Place a ships {ship_len}.")
            while True:
                x = input("Input ship start coordinate x: ")
                y = input("Input ship start coordinate y: ")
                try:
                    x = int(x)
                    y = int(y)
                except:
                    print("Ship coordinates must be an int")
                    break
                if ship_len > 1:
                    hz = input("The ship has a horizontal position (y/n): ")
                    if re.search(r'[Yy](es)?', hz) or '':
                        hz_pos = True
                    else:
                        hz_pos = False
                else:
                    hz_pos=True

                try:
                    self.add_ship(Ship((x, y), horizontal=hz_pos, length=ship_len))
                except IndexError or ValueError as e:
                    print(repr(e))
                    print("Try again")
                except:
                    print(f"You did something wrong. Try again")
                else:
                    break

    def add_ship(self, ship: Ship):
        for x, y in ship.coord:
            if not (0 <= x <= self.field_size or 0 <= y <= self.field_size):
                LOG.debug(f"Ship coordinates not in field, x: {x}, y: {y}")
                raise IndexError("Ship coordinates not in field")
            if (x, y) not in self._playable_cells:
                LOG.debug(f"You can't place the ship on this cell, x: {x}, y: {y}")
                raise ValueError("You can't place the ship on this cell")
            if self.find_cell_in_ships_or_border(x, y):
                LOG.debug(f"You can't place the ship on the other one, x: {x}, y: {y}")
                raise ValueError("You can't place the ship on the other one")
        self.ships.append(ship)
        return True

    def find_cell_in_ships_or_border(self, x, y):
        for ship in self.ships:
            ship_border = self.get_ship_border(ship.coord)
            if ship.check_my_coord(x, y) or (x, y) in ship_border:
                return True
        return False

    def get_ship_border(self, ship_coord: frozenset):
        to_mark = set()
        for s_x, s_y in ship_coord:
            dot_splash = set((s_x + x, s_y + y) for x in range(-1, 2) for y in range(-1, 2))
            to_mark.update((dot_splash - ship_coord) & self._playable_cells)
        LOG.debug(f"Ship border: {to_mark}")
        return to_mark

    def exclude_ship_border(self, ship_coord: frozenset):
        border = self.get_ship_border(ship_coord)
        self._playable_cells = self._playable_cells - border
        LOG.debug(f"Available cell: {self._playable_cells}")

    def mark_ship_border(self, ship_coord: frozenset, field):
        LOG.debug("mark the ship border")
        border = self.get_ship_border(ship_coord)
        for x, y in border:
            field[y][x] = self.field_cell_map['occupied']

    def shot(self, x: int, y: int):
        result = False
        if (x, y) not in self._playable_cells:
            raise ValueError("Shut to not properly cell")
        print(f"Shot to x: {x}, y: {y}")
        for ship in self.ships:
            result = ship.check_shot(x, y)
            if result:
                print("Hit!")
                if ship.life == 0:
                    print("Gotcha")
                    result = -1
                    self.__mark_ship(ship)
                else:
                    self.__field[y][x] = self.field_cell_map['hit']
                break
        else:
            print("Miss!")
            self.__field[y][x] = self.field_cell_map['miss']
        self.steps.update((x, y))
        self._playable_cells.remove((x, y))
        return result

    def __mark_ship(self, ship, field=None):
        LOG.debug("Mark the ship as dead")
        if not field:
            field = self.__field
        self.mark_ship_border(ship.coord, field)
        self.exclude_ship_border(ship.coord)
        for x, y in ship.coord:
            field[y][x] = self.field_cell_map['dead']

    def print_field(self, hide=True):
        # head
        print('    ', ' | '.join([str(x) for x in range(self.field_size)]))
        f = self.__field if hide else deepcopy(self.__field)
        if not hide:
            for ship in self.ships:
                self.mark_ship_border(ship_coord=ship.coord, field=f)
                for x, y in ship.coord:
                    f[y][x] = self.field_cell_map['ship']
        for i, l in enumerate(f):
            print(f" {i} |", ' | '.join(l))

    def place_random_ships(self):
        LOG.info("Try create the random pool of ships")
        start_time = time()
        now = time()
        while now - start_time < 20:
            now = time()
            for ship_len in sorted(reduce(lambda s, x: s + [x[0]]*x[1], self.available_ships.items(), []), reverse=True):
                res = self.try_install_random_ship(ship_len)
                if not res:
                    # Can't add one ship, try create all ships again
                    break
            else:
                # all ships added
                break
            self.ships = []
        else:
            raise RuntimeError("Can't create a pool random ships")

    def try_install_random_ship(self, ship_length):
        attempts = self._playable_cells.copy()

        def place_ship(_):
            nonlocal attempts
            coord = random.choice(list(attempts))
            LOG.debug(f"Try to place ship on {coord}")
            for hz in True, False:
                sh = Ship(coord, horizontal=hz, length=ship_length)
                try:
                    res = self.add_ship(sh)
                except ValueError:
                    continue
                if res:
                    return sh
            attempts.remove(coord)

        for s in map(place_ship, self._playable_cells):
            if s:
                return True
        return False

    @property
    def ships_remain(self):
        return [x for x in self.ships if x.life > 0]


class Game:
    def __init__(self, field_size=7):
        self.field_size = field_size
        self.player1, self.player2 = self.setup_players()

    def setup_players(self):
        player = Player(Field(self.field_size), robot=False)
        player.init_player()
        robo_field = Field(self.field_size)
        robo_field.place_random_ships()
        robot = Brain(robo_field)
        players = [player, robot]
        answ = input("do you want to do a first host [Y]es/no: ")
        return players if re.search(r'[Yy](es)*', answ if answ else 'Y') else players[::-1]

    def play(self):
        players_pool = [self.player1, self.player2]
        print("It's time to shot")
        while True:
            system('clear')
            for p in players_pool:
                ship_counter = Counter([s.length for s in p.playground.ships_remain])
                print(f"{p.name}'s ships remain:")
                for l, c in ship_counter.items():
                    print(f"Length: {l} - {c}")
            duck = players_pool.pop()
            active_player = players_pool.pop()
            print(f"{active_player} turn")
            if active_player.robot:
                res = active_player.shot_next(duck.playground)
            else:
                count = 0
                while count < 4:
                    duck.playground.print_field()
                    try:
                        res = duck.playground.shot(*self.get_shot_coord())
                    except ValueError:
                        print(f"Not proper cell for shot. Try again")
                        count += 1
                    else:
                        break
                if count > 3:
                    raise SyntaxError("User behavior is bad (.")
            print('-'*20)
            print()

            duck.playground.print_field()
            players_pool = [duck, active_player] if not res else [active_player, duck]
            if not duck.playground.ships_remain:
                self.win(active_player)
                break
            sleep(2)

    @staticmethod
    def get_shot_coord():
        count = 0
        while count < 3:
            x = input("Input shot coordinate x: ")
            y = input("Input shot coordinate y: ")
            try:
                x = int(x)
                y = int(y)
            except ValueError as e:
                print("Coordinate must be INT")
            else:
                return x, y
            count += 1

    @staticmethod
    def win(player):
        print(f"Player {player} win!")
        print(f"Player do {len(player.playground.steps)} steps")
        sys.exit()

# TODO now:
#   - ask about exit from cycle; clear ships
# TODO end:
#   - fix classes brain-player
#   - add random to horizontal when create a random ships
#   - place big ships on border for field size <=6
#   - Remove DEBUG from basic log