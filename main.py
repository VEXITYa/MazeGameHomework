import pygame
from typing import *
from random import choice
from copy import deepcopy
from queue import PriorityQueue

cells_x = 31

FPS = 30
PATH = True
GROUND = False
UP = 0
DOWN = 1
LEFT = 2
RIGHT = 3

selected_color = (232, 78, 15)
path_color = (149, 27, 129)
ground_color = (41, 13, 70)
lines_color = (149, 27, 129)
player_color = (0, 138, 209)
xz_color = (230, 0, 126)
cur_location = (1, 0)
pygame.font.init()
MAIN_FONT = pygame.font.Font('golos-ui_medium.ttf', 50)

pygame.init()
_width = pygame.display.Info().current_w * 0.9
cells_size = _width // cells_x
cells_y = int(cells_x * (9 / 16))
WIDTH = cells_x * cells_size + 1
HEIGHT = cells_y * cells_size + 1
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Maze")
clock = pygame.time.Clock()

Location = Tuple[int, int]


def heuristic(a: Location, b: Location) -> float:
    x1, y1 = a[0], a[1]
    x2, y2 = b[0], b[1]
    return abs(x1 - x2) + abs(y1 - y2)


class RectangleGrid:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.matrix: list[list[bool]] = [[GROUND for _ in range(self.width)] for _ in range(self.height)]
        self.__used: list[list[bool]] = deepcopy(self.matrix)
        self.shortest_path: list[Location] = []
        for row in range(self.height):
            for col in range(self.width):
                if (row % 2 != 0 and col % 2 != 0) and (row < height - 1 and col < width - 1):
                    self.matrix[row][col] = PATH

    def in_bounds(self, cell: Location) -> bool:
        return 0 <= cell[0] < self.width and 0 <= cell[1] < self.height

    def passable(self, cell: Location) -> bool:
        return self.matrix[cell[1]][cell[0]]

    def get_player_moves(self, cell: Location) -> list:
        x, y = cell[0], cell[1]
        neighbors = [(x + 1, y), (x - 1, y), (x, y - 1), (x, y + 1)]
        results = filter(self.in_bounds, neighbors)
        results = filter(self.passable, results)
        return list(results)

    def get_neighbours(self, cell: Location) -> Iterator[Location]:
        x, y = cell[0], cell[1]
        neighbors = [(x + 1, y), (x - 1, y), (x, y - 1), (x, y + 1)]
        if (x + y) % 2 == 0:
            neighbors.reverse()

        results = filter(self.in_bounds, neighbors)
        results = filter(self.passable, results)
        results = filter(lambda cur: not self.__used[cur[1]][cur[0]], results)
        return results

    def __get_neighbours_for_maze(self, cell: Location) -> Iterator[Location]:
        x, y = cell[0], cell[1]
        neighbors = [(x + 2, y), (x - 2, y), (x, y - 2), (x, y + 2)]
        results = filter(self.in_bounds, neighbors)
        results = filter(lambda cur: not self.__used[cur[1]][cur[0]], results)
        return results

    def __remove_wall(self, first: Location, second: Location):
        x_diff: int = second[0] - first[0]
        y_diff: int = second[1] - first[1]
        add_x = ((x_diff // abs(x_diff)) if x_diff != 0 else 0)
        add_y = ((y_diff // abs(y_diff)) if y_diff != 0 else 0)
        target = (first[0] + add_x, first[1] + add_y)
        self.matrix[target[1]][target[0]] = PATH
        self.__used[target[1]][target[0]] = True

    def __reconstruct_path(self, came_from: dict[Location, Location],
                           start: Location, goal: Location) -> list[Location]:
        current: Location = goal
        path: list[Location] = [(self.width - 1, self.height - 2)]
        if goal not in came_from.keys():
            return []
        while current != start:
            path.append(current)
            current = came_from[current]
        path.append(start)
        path.reverse()
        return path

    def generate_path(self, start: Location = (1, 0)):
        cur = (1, 1)
        stack = []

        while True:
            self.__used[cur[1]][cur[0]] = True
            neighbours = list(self.__get_neighbours_for_maze(cur))

            if len(neighbours) > 0:
                randcell = choice(neighbours)
                self.__used[randcell[1]][randcell[0]] = True
                stack.append(cur)
                self.__remove_wall(cur, randcell)
                cur = randcell
            elif stack:
                cur = stack.pop()
            else:
                break
        self.matrix[0][1] = PATH
        self.matrix[self.height - 2][self.width - 1] = PATH

    def find_shortest_path(self, player: Location):
        self.__used = [[False for _ in range(self.width)] for _ in range(self.height)]
        start = player
        goal = (self.width - 2, self.height - 2)
        frontier = PriorityQueue()
        frontier.put((0, (start[0], start[1])))
        came_from: dict[Location, Optional[Location]] = {start: None}
        cost_so_far: dict[Location, float] = {start: 0}
        self.__used[start[1]][start[0]] = True

        while not frontier.empty():
            current = frontier.get()[1]
            if current == goal:
                break
            new_cost = cost_so_far[current] + 1
            for next_ in self.get_neighbours(current):
                if next_ not in cost_so_far or new_cost < cost_so_far[next_]:
                    cost_so_far[next_] = new_cost
                    priority = new_cost + heuristic(next_, goal)
                    frontier.put((priority, next_))
                    came_from[next_] = current
                    self.__used[next_[1]][next_[0]] = True

        return self.__reconstruct_path(came_from, start, goal)


class Menu:
    def __init__(self):
        self._option_surfaces = []
        self._callbacks = []
        self._current_option = 0
        self._controls = [MAIN_FONT.render("Controls:", True, selected_color),
                          MAIN_FONT.render("1 - generate map", True, selected_color),
                          MAIN_FONT.render("2 - show path", True, selected_color),
                          MAIN_FONT.render("wasd/arrows - move", True, selected_color),
                          MAIN_FONT.render("esc - menu", True, selected_color),
                          ]

    def append_option(self, option, callback):
        self._option_surfaces.append(MAIN_FONT.render(option, True, selected_color))
        self._callbacks.append(callback)

    def switch(self, direction):
        self._current_option = max(0, min(self._current_option + direction, len(self._option_surfaces) - 1))

    def select(self):
        self._callbacks[self._current_option]()

    def draw(self, window: pygame.display, x: int, y: int, option_y_padding: int):
        for i, option in enumerate(self._option_surfaces):
            option_rect = option.get_rect()
            option_rect.topleft = (x, y + i * option_y_padding)
            if i == self._current_option:
                pygame.draw.rect(window, xz_color, option_rect)
            window.blit(option, option_rect)
        for i, cont in enumerate(self._controls):
            option_rect = cont.get_rect()
            option_rect.topleft = (x + 300, y + i * option_y_padding)
            window.blit(cont, option_rect)


Map = RectangleGrid(cells_x, cells_y)
Map.generate_path()
path = Map.find_shortest_path(cur_location)
i = 0


def draw_path(color):
    for row in range(Map.height):
        for col in range(Map.width):
            if Map.matrix[row][col] == PATH:
                pygame.draw.rect(window, color, [col * cells_size, row * cells_size, cells_size, cells_size])
    pygame.draw.rect(window, xz_color,[(Map.width - 1) * cells_size, (Map.height - 2) * cells_size, cells_size, cells_size])


def draw_short_path(color):
    global i, path
    keys = pygame.key.get_pressed()
    for cell in range(len(path)):
        pygame.draw.rect(window, color, [path[cell][0] * cells_size, path[cell][1] * cells_size, cells_size, cells_size])
    pygame.draw.rect(window, xz_color,[(Map.width - 1) * cells_size, (Map.height - 2) * cells_size, cells_size, cells_size])


def draw_player(color, cur_location: Location):
    pygame.draw.rect(window, color, [cur_location[0] * cells_size, cur_location[1] * cells_size, cells_size, cells_size])


def move_player(direction: int):
    global cur_location, path
    if direction == UP:
        if (cur_location[0], cur_location[1] - 1) in Map.get_player_moves(cur_location):
            cur_location = (cur_location[0], cur_location[1] - 1)
    elif direction == DOWN:
        if (cur_location[0], cur_location[1] + 1) in Map.get_player_moves(cur_location):
            cur_location = (cur_location[0], cur_location[1] + 1)
    elif direction == LEFT:
        if (cur_location[0] - 1, cur_location[1]) in Map.get_player_moves(cur_location):
            cur_location = (cur_location[0] - 1, cur_location[1])
    elif direction == RIGHT:
        if (cur_location[0] + 1, cur_location[1]) in Map.get_player_moves(cur_location):
            cur_location = (cur_location[0] + 1, cur_location[1])
    path = Map.find_shortest_path(cur_location)


def map_update():
    global Map, path, cur_location
    keys = pygame.key.get_pressed()
    if keys[pygame.K_1]:
        Map = RectangleGrid(cells_x, cells_y)
        Map.generate_path()
        cur_location = (1, 0)
        path = Map.find_shortest_path(cur_location)


def player_update():
    global cur_location, Map, path
    draw_player(player_color, cur_location)
    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        move_player(UP)
    elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
        move_player(DOWN)
    elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
        move_player(LEFT)
    elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        move_player(RIGHT)
    if cur_location == (cells_x - 1, cells_y - 2):
        Map = RectangleGrid(cells_x, cells_y)
        Map.generate_path()
        cur_location = (1, 0)
        path = Map.find_shortest_path(cur_location)


def path_update():
    keys = pygame.key.get_pressed()
    if keys[pygame.K_2]:
        draw_short_path(selected_color)


def set_mode(_cells_x: int):
    global cells_y, cells_size, cells_x, WIDTH, HEIGHT, window
    cells_x = _cells_x
    cells_size = _width // cells_x
    cells_y = int(cells_x * (9 / 16))
    cells_y = (cells_y if cells_y % 2 != 0 else cells_y + 1)
    WIDTH = cells_x * cells_size + 1
    HEIGHT = cells_y * cells_size + 1
    window = pygame.display.set_mode((WIDTH, HEIGHT))


def set_easy_mode():
    set_mode(31)


def set_medium_mode():
    set_mode(71)


def set_hard_mode():
    set_mode(111)


def set_hardest_mode():
    set_mode(151)


def main():
    draw_path(path_color)
    map_update()
    path_update()
    player_update()


menu = Menu()
menu.append_option("Easy", set_easy_mode)
menu.append_option("Medium", set_medium_mode)
menu.append_option("Hard", set_hard_mode)
menu.append_option("????????", set_hardest_mode)
menu.append_option("Quit", pygame.quit)

run = True
menu_opened = True
while run:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                menu_opened = not menu_opened
            if menu_opened:
                if event.key == pygame.K_DOWN:
                    menu.switch(1)
                elif event.key == pygame.K_UP:
                    menu.switch(-1)
                if event.key == pygame.K_RETURN:
                    menu.select()
                    menu_opened = not menu_opened
                    Map = RectangleGrid(cells_x, cells_y)
                    Map.generate_path()
                    cur_location = (1, 0)
                    path = Map.find_shortest_path(cur_location)

    window.fill(ground_color)
    if not menu_opened:
        main()
    else:
        menu.draw(window, 100, 100, 75)
    pygame.display.update()
    clock.tick(FPS)

pygame.quit()
