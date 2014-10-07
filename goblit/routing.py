import os.path
import pygame.image
from math import sqrt
from itertools import product


PLAN_DIR = 'data/'

YSCALE = 0.3


class Grid:
    GRID_COLOR = (255, 0, 255)
    YSCALE = 0.9

    def _n(x, y):
        ys = y / YSCALE
        return sqrt(x * x + ys * ys), (x, y)

    NEIGHBOURS = [
        _n(-1, 0),
        _n(1, 0),
        _n(0, 1),
        _n(0, -1),
        _n(1, 1),
        _n(1, -1),
        _n(-1, 1),
        _n(-1, -1),

        # Additional neighbours offer additional (smoother) directions
        _n(-2, -1),
        _n(-2, 1),
        _n(2, -1),
        _n(2, 1),

        _n(-1, 2),
        _n(1, 2),
        _n(-1, -2),
        _n(1, -2),
    ]

    def __init__(self, surf, subdivide):
        self.surf = surf
        self.w, self.h = self.surf.get_size()
        self.subdivide = subdivide

    @classmethod
    def load(cls, name, subdivide=(15, 5)):
        path = os.path.join(PLAN_DIR, name + '.png')
        surf = pygame.image.load(path)
        w, h = surf.get_size()
        subx, suby = subdivide
        subw, subh = w // subx, h // suby
        subsampled = pygame.Surface((subw, subh))
        threshold = subx * suby // 2
        for x, y in product(range(subw), range(subh)):
            ox = x * subx
            oy = y * suby
            orig_pixels = product(
                range(ox, min(ox + subx, w)),
                range(oy, min(oy + suby, h))
            )
            ingrid = sum(
                surf.get_at(pos) == cls.GRID_COLOR for pos in orig_pixels)
            if ingrid > threshold:
                subsampled.set_at((x, y), cls.GRID_COLOR)
        return cls(subsampled, subdivide)

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
        for cost, (ox, oy) in self.NEIGHBOURS:
            px = x + ox
            py = y + oy
            if 0 <= px < w and 0 <= py < h:
                p = px, py
                in_grid = self.surf.get_at(p) == self.GRID_COLOR
                if in_grid:
                    yield cost, p

    def __contains__(self, pos):
        pos = self.screen_to_subsampled(pos)
        px, py = pos
        if 0 <= px < self.w and 0 <= py < self.h:
            p = px, py
            return self.surf.get_at(p) == self.GRID_COLOR
        return False

    def _route(self, pos, goal):
        """Find a route from pos to goal.

        Basically a transliteration of the A* algorithm psuedocode at
        http://en.wikipedia.org/wiki/A*_search_algorithm

        """
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

    def screen_to_subsampled(self, pos):
        x, y = pos
        sx, sy = self.subdivide
        return x // sx, y // sy

    def route(self, pos, goal):
        if pos not in self:
            raise ValueError("Source is not in grid")
        if goal not in self:
            raise ValueError("Goal is not in grid")

        r = self._route(
            self.screen_to_subsampled(pos),
            self.screen_to_subsampled(goal),
        )
        sx, sy = self.subdivide
        r = [(sx * x, sy * y) for x, y in r]
        r[-1] = goal
        return r

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
        if len(route) > 1:
            pygame.draw.lines(screen, Grid.GRID_COLOR, False, route)
        screen.blit(grid.surf, (0, 0))
        pygame.display.flip()

    room = pygame.image.load('graphics/room.png')
    pygame.init()
    screen = pygame.display.set_mode(room.get_size())

    draw_route()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.pos in grid:
                    pts = [pts[1], ev.pos]
                else:
                    print("Not in grid")
                draw_route()
