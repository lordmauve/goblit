from math import sqrt


YSCALE = 0.3


def dist(p1, p2):
    """Get the floor distance between two points"""
    x, y = p1
    tx, ty = p2
    dx = tx - x
    dy = (ty - y) / YSCALE
    return sqrt(dx * dx + dy * dy)
