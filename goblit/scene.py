from math import sqrt
from collections import deque

import pygame.mouse
from pygame.cursors import load_xbm

from .loaders import load_image
from .hitmap import HitMap
from .navpoints import points_from_svg
from .routing import Grid
from . import clock
from . import scripts
from .geom import dist


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


class Scene:
    def __init__(self):
        self.room_bg = None
        self.room_fg = None
        self.objects = []
        self.actors = {}
        self.navpoints = {}
        self.object_scripts = {}
        self.hitmap = None
        self.bubble = None
        self.animations = []
        self.grid = None
        self._on_animation_finish = []

    def get_actor(self, name):
        """Get the named actor."""
        return self.actors.get(name)

    def get(self, name):
        """Get the named thing."""
        return (
            self.actors.get(name) or
            self.navpoints.get(name) or
            self.hitmap.get_point(name)
        )

    def __getitem__(self, name):
        """Get the named thing."""
        o = self.get(name)
        if not o:
            raise KeyError(name)

    def load(self):
        self.room_bg = load_image('room')
        self.room_fg = load_image('foreground')
        self.hitmap = HitMap.from_svg('hit-areas')
        self.navpoints = points_from_svg('navigation-points')
        self.grid = Grid.load('floor')

    def init_scene(self):
        from .actors import Goblit, Tox
        self.actors['GOBLIT'] = Goblit(self, (100, 400))
        self.actors['WIZARD TOX'] = Tox(self, (719, 339), initial='sitting-at-desk')
        clock.each_tick(self.update)

    def say(self, actor_name, text):
        from .actors import SpeechBubble
        actor = self.get_actor(actor_name)
        if not actor:
            raise ScriptError("Actor %s is not on set" % text)
        self.bubble = SpeechBubble(text, actor)
        if actor_name != 'GOBLIT':
            goblit = self.get_actor('GOBLIT')
            if goblit:
                goblit.face(actor)

    def action_text(self, msg):
        from .actors import FontBubble
        self.bubble = FontBubble(msg, pos=(480, 440))

    def close_bubble(self):
        self.bubble = None

    def move(self, actor, goal, on_move_end=None):
        npcs = [a.pos for a in self.actors.values() if a != actor]
        route = self.grid.route(actor.pos, goal, npcs=npcs)
        self.animations.append(Move(route, actor, on_move_end=on_move_end))

    def update(self, dt):
        for a in self.animations:
            a.update(dt)

    def skip_animation(self):
        for a in self.animations:
            a.skip()

    def end_animation(self, a):
        self.animations.remove(a)
        if not self.animations:
            self._fire_on_animation_finish()

    def on_animation_finish(self, callback):
        self._on_animation_finish.append(callback)

    def _fire_on_animation_finish(self):
        for c in self._on_animation_finish:
            try:
                c()
            except Exception:
                import traceback
                traceback.print_exc()
        del self._on_animation_finish[:]

    def draw(self, screen):
        screen.blit(self.room_bg, (0, 0))
        rh = self.room_bg.get_height()
        sw, sh = screen.get_size()
        screen.fill((0, 0, 0), pygame.Rect(0, rh, sw, sh - rh))

        actors = sorted(self.actors.values(), key=lambda a: a.pos[1])
        for o in actors:
            o.draw(screen)
        screen.blit(self.room_fg, (0, 0))

        if self.bubble:
            self.bubble.draw(screen)

    def action_for_point(self, pos):
        for name, a in self.actors.items():
            if a.bounds.collidepoint(pos) and name != 'GOBLIT':
                return 'Speak to %s' % name, lambda: player.speak_to(name)

        r = self.hitmap.region_for_point(pos)
        if r:
            if r in scene.object_scripts:
                script = scene.object_scripts[r]
                return 'Look at %s' % r, lambda: self.play_subscript(pos, script)

    def play_subscript(self, pos, script):
        a = scene.get_actor('GOBLIT')
        a.face(pos)
        player.play_subscript(script)


class Cursor:
    pointer = None

    @classmethod
    def load(cls):
        cls.DEFAULT = pygame.mouse.get_cursor()
        cls.POINTER = load_xbm('data/hand.xbm', 'data/hand-mask.xbm')

    @classmethod
    def _set(cls, pointer):
        if cls.pointer != pointer:
            pygame.mouse.set_cursor(*pointer)
            cls.pointer = pointer

    @classmethod
    def set_default(cls):
        cls._set(cls.DEFAULT)

    @classmethod
    def set_pointer(cls):
        cls._set(cls.POINTER)


class ScriptError(Exception):
    """A state problem means a script step can't play."""


class ScriptPlayer:
    def __init__(self, script, clock, on_finish=None):
        self.clock = clock
        self.stack = []
        self.skippable = False  # If we can safely skip the delay
        self.on_finish = on_finish
        self.play_subscript(script)

    @property
    def script(self):
        return self.stack[-1][0]

    @property
    def step(self):
        return self.stack[-1][1]

    @step.setter
    def step(self, v):
        self.stack[-1][1] = v

    @property
    def waiting(self):
        return self.stack[-1][2]

    @waiting.setter
    def waiting(self, v):
        self.stack[-1][2] = v

    def play_subscript(self, script):
        self.stack.append([script, 0, None])
        self.next()

    def end_subscript(self):
        self.stack.pop()

    def next(self):
        if self.step >= len(self.script.contents):
            if len(self.stack) > 1:
                self.end_subscript()
                if not self.waiting:
                    self.do_next()
            else:
                self.on_finish()
            return
        self.skippable = False
        instruction = self.script.contents[self.step]
        self.step += 1
        op = type(instruction).__name__.lower()
        handler = getattr(self, 'do_' + op, None)
        try:
            if not handler:
                raise ScriptError("No handler for op %s" % op)
            handler(instruction)
        except ScriptError as e:
            print(e.args[0])
            self.do_next()
        except Exception:
            import traceback
            traceback.print_exc()
            self.do_next()

    def skip(self):
        if self.skippable:
            self.clock.unschedule(self.cancel_line)
            self.clock.unschedule(self.next)
            scene.close_bubble()
            if scene.animations:
                scene.skip_animation()
            else:
                self.next()

    def speak_to(self, target):
        if self.waiting and self.waiting.verb == 'Speak to %s' % target:
            self.waiting = None
            self.do_next()

    def do_next(self):
        if scene.animations:
            self.skippable = True
            scene.on_animation_finish(self.do_next)
        else:
            self.schedule_next(0)

    def schedule_next(self, delay=2):
        self.clock.unschedule(self.next)  # In case we're already scheduled
        self.clock.schedule(self.next, delay)

    def cancel_line(self):
        scene.close_bubble()
        self.next()

    def do_line(self, line):
        scene.say(line.character, line.line)
        self.clock.schedule(self.cancel_line, 3)
        self.skippable = True

    def do_pause(self, pause):
        self.schedule_next()
        self.skippable = True

    def do_action(self, action):
        self.waiting = action

    def do_stagedirection(self, d):
        actor = scene.get_actor(d.character)
        if not actor:
            raise ScriptError("Actor %s is not on set" % d.character)
        handler = actor.stage_directions.get(d.verb)
        if not handler:
            raise ScriptError(
                "Unsupported stage direction %r for %s" % (d.verb, d.character)
            )
        if d.object:
            object = scene.get(d.object)
            if not object:
                raise ScriptError("%s is not on set" % d.object)
            handler(actor, object)
        else:
            handler(actor)
        self.do_next()

    def do_directive(self, directive):
        name = directive.name
        handler = getattr(self, 'directive_' + name, None)
        if not handler:
            raise ScriptError("No handler for directive %s" % name)
        handler(directive)

    def directive_onclick(self, directive):
        scene.object_scripts[directive.data.strip()] = directive
        self.do_next()


# Script player
player = None
scene = None


def load():
    global player, scene
    scene = Scene()
    scene.load()
    Cursor.load()

    s = scripts.parse_file('script.txt')
    player = ScriptPlayer(s, clock)

    scene.init_scene()


def on_mouse_down(pos, button):
    if button == 3 and player.skippable:
        player.skip()
        return

    if button == 1 and player.waiting:
        r = scene.action_for_point(pos)
        if r:
            r[1]()
            Cursor.set_default()
        else:
            goblit = scene.get_actor('GOBLIT')
            if goblit:
                try:
                    goblit.move_to(pos)
                except ValueError:
                    pass


def on_mouse_move(pos, rel, buttons):
    global bubble

    if not player.waiting:
        return

    r = scene.action_for_point(pos)
    if r:
        Cursor.set_pointer()
        scene.action_text(r[0])
    else:
        Cursor.set_default()
        scene.close_bubble()


def update(dt):
    clock.tick(dt)


def draw(screen):
    scene.draw(screen)

#   Uncomment to enable debugging of routing
#    g = scene.grid.build_npcs_grid([a.pos for a in scene.actors.values()])
#    screen.blit(g.surf, (0, 0))
