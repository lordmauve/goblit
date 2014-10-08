import pygame
from pygame.font import Font
from .animations import Sequence, Frame, Animation, loop
from .loaders import load_image, load_frames
from .geom import dist
from .actions import Action


def load_sequence(base, num, offset):
    fs = []
    for f in load_frames(base, num):
        fs.append(Frame(f, offset))
    return fs


GOBLIT = Animation({
    'default': Sequence([
        Frame(load_image('goblit-standing'), (-18, -81))
    ], loop),
    'walking': Sequence(
        load_sequence('goblit-walking', 4, (-46, -105)), loop),
    'look-back': Sequence([
        Frame(load_image('goblit-back'), (-18, -81))
    ], loop)
})

TOX = Animation({
    'default': Sequence([
        Frame(load_image('tox-standing'), (-31, -95))
    ], loop),
    'sitting-at-desk': Sequence([
        Frame(load_image('tox-sitting-desk'), (-37, -99))
    ], loop),
    'sitting': Sequence([
        Frame(load_image('tox-sitting'), (-41, -91))
    ], loop)
})

FONT_NAME = 'fonts/RosesareFF0000.ttf'
FONT = Font(FONT_NAME, 16)


class FontBubble:
    def __init__(self, text, pos=(0, 0), color=(255, 255, 255)):
        self.text = text
        self.pos = pos
        self.color = color
        self._build_surf()

    def _build_surf(self):
        base = FONT.render(self.text, False, self.color)
        black = FONT.render(self.text, False, (0, 0, 0))

        w, h = base.get_size()
        self.surf = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)

        for off in [(0, 0), (0, 2), (2, 0), (2, 2)]:
            self.surf.blit(black, off)

        self.surf.blit(base, (1, 1))

    def draw(self, screen):
        x, y = self.pos
        w = self.surf.get_width()
        x = min(max(10, x - w // 2), 950 - w)
        screen.blit(self.surf, (x, y))


class SpeechBubble(FontBubble):
    def __init__(self, text, actor):
        x, y = actor.sprite.pos
        super().__init__(text, (x, y - 120), actor.COLOR)


ACTORS = []


class ActorMeta(type):
    def __new__(cls, name, bases, dict):
        stage_directions = {}
        for b in reversed(bases):
            try:
                stage_directions.update(b.stage_directions)
            except AttributeError:
                pass
        for k, v in list(dict.items()):
            if callable(v):
                verb = getattr(v, 'stage_direction', None)
                if verb:
                    stage_directions[verb] = v

        dict['stage_directions'] = stage_directions
        t = type.__new__(cls, name, bases, dict)
        if 'NAME' in dict:
            ACTORS.append(t)
        return t


def stage_direction(name):
    """Decorator to mark a method as a stage direction."""
    def decorator(func):
        func.stage_direction = name
        return func
    return decorator


class Actor(metaclass=ActorMeta):
    def __init__(self, scene):
        self.scene = scene
        self.sprite = None
        self.visible = False
        self.name = self.NAME

        frame = self.SPRITE.sequences['default'].frames[0]
        r = frame.sprite.get_rect()
        self._bounds = r.move(*frame.offset)

    def show(self, pos=None, dir='right', initial='default'):
        self.visible = True
        self.sprite = self.SPRITE.create_instance(pos or self._last_pos)
        self.sprite.dir = 'right'

    def hide(self):
        self._last_pos = self.sprite.pos
        self.sprite = None

    @property
    def pos(self):
        return self.sprite.pos

    @pos.setter
    def pos(self, pos):
        if self.sprite:
            self.sprite.pos = pos

    @property
    def z(self):
        """Z-index of actor in scene is related to y-coordinate."""
        return self.sprite.pos[1]

    @property
    def bounds(self):
        return self._bounds.move(*self.sprite.pos)

    def draw(self, screen):
        self.sprite.draw(screen)

    def click_actions(self):
        return [Action('Speak to %s' % self.NAME, self.click)]

    def click(self):
        actor = self.scene.get_actor('GOBLIT')
        if actor:
            point = self.scene.nearest_navpoint(self.pos)
            actor.move_to(point, on_move_end=lambda: actor.face(self), strict=False)

    @stage_direction('turns to face')
    def face(self, obj):
        if isinstance(obj, tuple):
            pos = obj
        else:
            pos = obj.pos
        px = self.sprite.pos[0]
        if px < pos[0]:
            self.sprite.dir = 'right'
        elif px > pos[0]:
            self.sprite.dir = 'left'
        self.sprite.play('default')

    @stage_direction('moves to')
    def move_to(self, pos, on_move_end=None, strict=True, exclusive=False):
        if self.visible and dist(pos, self.pos) > 5:
            self.scene.move(
                self, pos,
                on_move_end=on_move_end,
                strict=strict,
                exclusive=exclusive
            )

    def move_to_point(self, navpoint, on_move_end=None):
        """Move to the named navpoint."""
        pos = self.scene.navpoints[navpoint]
        self.move_to(pos, on_move_end=on_move_end)

    @stage_direction('enters')
    def enter(self, navpoint='ENTRANCE'):
        """Enter via the door and walk to navpoint."""
        pos = self.scene.navpoints['DOOR']
        self.scene.spawn_actor(self.NAME, pos)
        self.move_to_point(navpoint)

    @stage_direction('leaves')
    def leave(self):
        """Walk out of the room."""
        if self.visible:
            self.move_to(
                'DOOR',
                on_move_end=lambda: self.scene.unspawn_actor(self)
            )

    @stage_direction('looks out of window')
    def look_out_of_window(self):
        self.move_to(
            self.scene.get('WINDOW'),
            on_move_end=lambda: self.sprite.play('look-back')
        )


class Goblit(Actor):
    NAME = 'GOBLIT'
    COLOR = (255, 255, 255)
    SPRITE = GOBLIT

    def click_action(self):
        """Clicking on Goblit does nothing."""
        return None


class Tox(Actor):
    NAME = 'WIZARD TOX'
    COLOR = (150, 50, 255)
    SPRITE = TOX

    @stage_direction('turns around')
    def turn_around(self):
        self.sprite.play('sitting')
        self.sprite.dir = 'left'

    @stage_direction('turns back to desk')
    def turn_back_to_desk(self):
        self.sprite.play('sitting-at-desk')
        self.sprite.dir = 'right'
