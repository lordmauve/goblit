import pygame.mouse
from pygame.cursors import load_xbm

from .loaders import load_image
from .hitmap import HitMap
from .clock import Clock
from . import scripts


room_bg = None
objects = []

ACTORS = {}
object_scripts = {}
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
    def __init__(self, script, clock, on_finish=None):
        self.clock = clock
        self.script = script
        self.step = 0
        self.skippable = False  # If we can safely skip the delay
        self.waiting = None  # If we're waiting for player action
        self.on_finish = on_finish

    def next(self):
        if self.step >= len(self.script.contents):
            self.on_finish()
            return
        self.skippable = False
        instruction = self.script.contents[self.step]
        self.step += 1
        op = type(instruction).__name__.lower()
        handler = getattr(self, 'do_' + op, None)
        if not handler:
            print("No handler for op %s" % op)
            self.schedule_next(0)
        else:
            handler(instruction)

    def skip(self):
        if self.skippable:
            self.clock.unschedule(self.cancel_line)
            self.clock.unschedule(self.next)
            self.next()

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
            self.clock.schedule(self.cancel_line, 3)
            self.skippable = True
        else:
            print("Actor %s is not on set" % line.character)
            self.schedule_next(0)

    def do_pause(self, pause):
        self.schedule_next()
        self.skippable = True

    def do_action(self, action):
        self.waiting = action

    def do_directive(self, directive):
        name = directive.name
        handler = getattr(self, 'directive_' + name, None)
        if not handler:
            print("No handler for directive %s" % name)
            self.schedule_next(0)
        else:
            handler(directive)

    def directive_onclick(self, directive):
        object_scripts[directive.data.strip()] = directive
        self.schedule_next(0)


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
    from .actors import Goblit, Tox
    ACTORS['GOBLIT'] = Goblit((100, 400))
    ACTORS['WIZARD TOX'] = Tox((719, 339), initial='sitting-at-desk')

    # goblit.say("Blimey, it's cold in here")
    hitmap = HitMap.from_svg('hit-areas')
    Cursor.load()

    s = scripts.parse_file('script.txt')
    player = ScriptPlayer(s, clock)
    player.next()


def on_mouse_down(pos, button):
    if button == 3 and player.skippable:
        player.skip()
        return

    if button == 1 and player.waiting:
        r = hitmap.region_for_point(pos)
        if r:
            #TODO: handle event for object
            pass



def on_mouse_move(pos, rel, buttons):
    if not player.waiting:
        pass

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
