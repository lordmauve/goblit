from collections import deque
from .geom import dist, screen_dist


class Move:
    V = 150  # Speed at which we move (pixels/s)

    def __init__(self, route, actor, on_move_end=None):
        self.actor = actor
        self.goal = route[-1]  # Final waypoint
        self.route = deque(route)  # Waypoints remaining
        self.last = self.pos  # Last waypoint we passed
        self.last_dt = 0  # Amount of time along last segment
        self.on_move_end = on_move_end
        self._next_point()
        self.actor.sprite.play('walking')
        self.total_duration = sum(
            dist(route[i], route[i + 1])
            for i in range(len(route) - 1)
        )

    @property
    def pos(self):
        return self.actor.sprite.pos

    def to_target(self):
        return dist(self.last, self.target)

    def _next_point(self):
        self.target = self.route.popleft()
        self.t = self.to_target() / self.V

    def skip(self):
        """Skip to the end of the move."""
        self.actor.sprite.pos = self.goal
        self.actor.scene.end_animation(self)
        self.actor.sprite.play('default')
        if self.on_move_end:
            self.on_move_end()

    def update(self, dt):
        dt += self.last_dt
        # Skip any segements we've moved past
        while dt > self.t:
            dt -= self.t
            if self.route:
                self.last = self.target
                self._next_point()
            else:
                self.skip()
                return

        # Interpolate the last segment
        frac = dt / self.t
        x, y = self.last
        tx, ty = self.target

        x = round(frac * tx + (1 - frac) * x)
        y = round(frac * ty + (1 - frac) * y)
        self.actor.sprite.pos = x, y
        self.last_dt = dt
        if tx > x:
            self.actor.sprite.dir = 'right'
        elif tx < x:
            self.actor.sprite.dir = 'left'


class MovingSprite:
    """Move a sprite on the screen."""
    def __init__(self, sprite, end, v=150, on_move_end=None):
        self.sprite = sprite
        self.start = sprite.pos
        self.end = end
        self.on_move_end = on_move_end
        self.t = 0
        self.total_duration = screen_dist(self.start, end) / v

    @property
    def pos(self):
        return self.sprite.pos

    def update(self, dt):
        self.t += dt
        frac = self.t / self.total_duration
        if frac >= 1:
            if self.on_move_end:
                self.on_move_end()
            return
        x, y = self.start
        tx, ty = self.end

        x = round(frac * tx + (1 - frac) * x)
        y = round(frac * ty + (1 - frac) * y)
        self.sprite.pos = x, y


class FallingSprite:
    """Animate a falling sprite on the screen."""
    GRAVITY = 500

    def __init__(self, sprite, vx, vy, endy, on_move_end=None):
        self.sprite = sprite
        self.vx = vx
        self.vy = 0
        self.f_pos = self.sprite.pos
        self.endy = endy
        self.on_move_end = on_move_end

    @property
    def pos(self):
        return self.sprite.pos

    def update(self, dt):
        dx = self.vx * dt
        uv = self.vy
        self.vy += self.GRAVITY * dt

        x, y = self.f_pos
        x += dx
        y += 0.5 * (uv + self.vy) * dt

        y = min(y, self.endy)

        self.f_pos = x, y
        self.sprite.pos = int(x), int(y)

        if y >= self.endy:
            if self.on_move_end:
                self.on_move_end()

