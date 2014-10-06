import pygame.mouse
from pygame.cursors import load_xbm

from .loaders import load_image
from .hitmap import HitMap
from .clock import Clock
from . import scripts


room_bg = None
objects = []

ACTORS = {}
hitmap = None


clock = Clock()


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


class ScriptPlayer:
    def __init__(self, script, clock):
        self.clock = clock
        self.script = script
        self.step = 0

    def next(self):
        instruction = self.script.contents[self.step]
        self.step += 1
        op = type(instruction).__name__.lower()
        handler = getattr(self, 'do_' + op, None)
        if not handler:
            print("No handler for op %s" % op)
            self.schedule_next(0)
        else:
            handler(instruction)

    def schedule_next(self, delay=2):
        self.clock.schedule(self.next, delay)

    def cancel_line(self):
        global bubble
        bubble = None
        self.next()

    def do_line(self, line):
        actor = ACTORS.get(line.character)
        if actor:
            say(actor, line.line)
        else:
            print("Actor %s is not on set" % line.character)
        self.clock.schedule(self.cancel_line, 3)


bubble = None


def say(actor, text):
    global bubble
    from .actors import SpeechBubble
    bubble = SpeechBubble(text, actor)


# Script player
player = None


def load():
    global room_bg, hitmap, player
    room_bg = load_image('room')
    from .actors import Goblit, SpeechBubble
    ACTORS['GOBLIT'] = Goblit()

    # goblit.say("Blimey, it's cold in here")
    hitmap = HitMap.from_svg('hit-areas')
    Cursor.load()

    s = scripts.parse_file('script.txt')
    player = ScriptPlayer(s, clock)
    player.next()


def on_mouse_move(pos, rel, buttons):
    r = hitmap.region_for_point(pos)
    if r:
        Cursor.set_pointer()
    else:
        Cursor.set_default()


def update(dt):
    clock.tick(dt)


def draw(screen):
    screen.blit(room_bg, (0, 0))

    drawables = list(ACTORS.values()) + objects
    for o in drawables:
        o.draw(screen)
    if bubble:
        bubble.draw(screen)
