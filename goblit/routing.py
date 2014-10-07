import os.path
import pygame.image
from math import sqrt


PLAN_DIR = 'data/'


class Grid:
    GRID_COLOR = (255, 0, 255)
    YSCALE = 0.2

    NEIGHBOURS = [
        (-1, 0),
        (1, 0),
        (0, 1),
        (0, -1)
    ]

    def __init__(self, surf):
        self.surf = surf
        self.w, self.h = self.surf.get_size()

    @classmethod
    def load(cls, name):
        path = os.path.join(PLAN_DIR, name + '.png')
        surf = pygame.image.load(path)
        return cls(surf)

    def cost(self, p1, p2):
        x1, y1 = p1
        x2, y2 = p2
        dx = x2 - x1
        dy = (y2 - y1) / self.YSCALE
        return sqrt(dx * dx + dy * dy)

    def neighbour_nodes(self, pos):
        x, y = pos
        w = self.w
        h = self.h
        for ox, oy in self.NEIGHBOURS:
            px = x + ox
            py = y + oy
            if 0 <= px < w and 0 <= py < h:
                p = px, py
                in_grid = self.surf.get_at(p) == self.GRID_COLOR
                if in_grid:
                    yield abs(oy / self.YSCALE) + abs(ox), p

    def __contains__(self, pos):
        px, py = pos
        if 0 <= px < self.w and 0 <= py < self.h:
            p = px, py
            return self.surf.get_at(p) == self.GRID_COLOR
        return False

    def route(self, pos, goal):
        """Find a route from pos to goal.

        Basically a transliteration of the A* algorithm psuedocode at
        http://en.wikipedia.org/wiki/A*_search_algorithm

        """
        if pos not in self:
            raise ValueError("Source is not in grid")
        if goal not in self:
            raise ValueError("Goal is not in grid")
        closedset = set()
        openset = set([pos])
        came_from = {}
        g_score = {pos: 0}
        f_score = {pos: self.cost(pos, goal)}

        cost = self.cost
        neighbour_nodes = self.neighbour_nodes
        inf = float('inf')

        while openset:
            current = min(openset, key=lambda pos: f_score.get(pos, inf))
            if current == goal:
                return self._reconstruct_path(came_from, goal)

            openset.remove(current)
            closedset.add(current)

            g_current = g_score[current]
            for step_cost, neighbour in neighbour_nodes(current):
                if neighbour in closedset:
                    continue

                tentative_g_score = g_current + step_cost

                if tentative_g_score < g_score.get(neighbour, inf):
                    came_from[neighbour] = current
                    g_score[neighbour] = tentative_g_score
                    f_score[neighbour] = tentative_g_score + cost(neighbour, goal)
                    openset.add(neighbour)

        raise ValueError("No path exists from %r to %r" % (pos, goal))

    def _reconstruct_path(self, came_from, goal):
        current_node = goal
        hist = [current_node]
        while True:
            current_node = came_from.get(current_node)
            if current_node is None:
                return reversed(hist)
            hist.append(current_node)


if __name__ == '__main__':
    import sys
    import time
    grid = Grid.load('floor')

    pts = [(695, 315), (856, 351)]

    def draw_route():
        try:
            start = time.time()
            route = grid.route(*pts)
            duration = (time.time() - start) * 1000
            print("Route calculated in %dms" % duration)
        except ValueError as e:
            print(e.args[0])
            route = []
        screen.blit(room, (0, 0))
        screen.lock()
        for pos in route:
            screen.set_at(pos, grid.GRID_COLOR)
        screen.unlock()
        pygame.display.flip()

    room = pygame.image.load('graphics/room.png')
    pygame.init()
    screen = pygame.display.set_mode(room.get_size())

    which = True

    draw_route()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                pts[which] = ev.pos
                which = not which
                draw_route()
