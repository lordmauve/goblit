import os.path
import pygame.image
from math import sqrt
from itertools import product
from operator import itemgetter


PLAN_DIR = 'data/'

YSCALE = 0.3

BLACK = (0, 0, 0)


class Grid:
    """A* Pathfinding on a grid layout of the floor."""
    GRID_COLOR = (255, 0, 255)

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
        _n(2, 0),
        _n(0, 2),
        _n(-2, 0),
        _n(0, -2),

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
        dy = (y2 - y1) / YSCALE
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

    def _route(self, pos, goal, strict=True):
        """Find a route from pos to goal.

        Basically a transliteration of the A* algorithm psuedocode at
        http://en.wikipedia.org/wiki/A*_search_algorithm

        If strict is False, return the path to the closest reachable point
        if there is no path to the given point.

        """
        closedset = set()
        openset = set([pos])
        came_from = {}
        g_score = {pos: 0}
        closest = pos
        closest_dist = self.cost(pos, goal)
        f_score = {pos: closest_dist}

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
                    d = cost(neighbour, goal)
                    if d < closest_dist:
                        closest = neighbour
                        closest_dist = d
                    f_score[neighbour] = tentative_g_score + d
                    openset.add(neighbour)

        if strict:
            raise ValueError("No path exists from %r to %r" % (pos, goal))

        return self._reconstruct_path(came_from, closest)

    def screen_to_subsampled(self, pos):
        x, y = pos
        sx, sy = self.subdivide
        return x // sx, y // sy

    def build_npcs_grid(self, npcs):
        """Build a map that excludes areas where NPCs are standing"""
        surf = pygame.Surface(self.surf.get_size())
        surf.blit(self.surf, (0, 0))
        r = pygame.Rect(0, 0, 100 // self.subdivide[0], 30 // self.subdivide[1])
        for pos in npcs:
            spos = self.screen_to_subsampled(pos)
            r.center = spos
            pygame.draw.ellipse(surf, BLACK, r)
        return Grid(surf, self.subdivide)

    def route(self, pos, goal, strict=True, npcs=None):
        if pos not in self:
            raise ValueError("Source is not in grid")
        if goal not in self and strict:
            raise ValueError("Goal is not in grid")

        if npcs:
            g = self.build_npcs_grid(npcs)
            try:
                return g.route(pos, goal, strict=strict)
            except ValueError:
                print("Failed to find route, now disregarding npcs.")
                pass

        r = self._route(
            self.screen_to_subsampled(pos),
            self.screen_to_subsampled(goal),
            strict=strict
        )
        sx, sy = self.subdivide
        r = [(sx * x, sy * y) for x, y in r]
        if strict:
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
