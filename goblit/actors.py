import pygame
from pygame.font import Font
from .animations import Sequence, Frame, Animation, loop
from .loaders import load_image, load_frames
from .geom import dist
from .actions import Action
from .errors import ScriptError
from .inventory import SceneItem


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
    'catapulting': Sequence([
        Frame(load_image('goblit-catapulting'), (-32, -83))
    ] * 10, 'default'),
    'blushing': Sequence([
        Frame(load_image('goblit-blushing'), (-18, -81))
    ] * 30, 'default'),
    'disgusted': Sequence([
        Frame(load_image('goblit-disgust'), (-18, -81))
    ] * 30, 'default'),
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
    ], loop),
    'walking': Sequence(
        load_sequence('tox-walking', 4, (-46, -105)), loop),
})

AMELIA = Animation({
    'default': Sequence([
        Frame(load_image('amelia-standing'), (-21, -87))
    ], loop),
    'angry': Sequence([
        Frame(load_image('amelia-angry'), (-21, -87))
    ], loop),
    'blushing': Sequence([
        Frame(load_image('amelia-blushing'), (-21, -87))
    ] * 30, 'default'),
    'disgusted': Sequence([
        Frame(load_image('amelia-disgust'), (-21, -87))
    ] * 30, 'default'),
    'walking': Sequence(
        load_sequence('amelia-walking', 4, (-46, -105)), loop),
})

RALPH = Animation({
    'default': Sequence([
        Frame(load_image('ralph-standing'), (-18, -82))
    ], loop),
    'walking': Sequence(
        load_sequence('ralph-walking', 4, (-46, -105)), loop),
})

JOAN = Animation({
    'default': Sequence([
        Frame(load_image('joan-standing'), (-22, -98))
    ], loop),
    'walking': Sequence(
        load_sequence('joan-walking', 4, (-46, -105)), loop),
})


CAULDRON = Animation({
    'default': Sequence([
        Frame(load_image('cauldron'), (-43, -95))
    ], loop),
    'full': Sequence([
        Frame(load_image('cauldron-full'), (-43, -95))
    ], loop),
    'bubbling': Sequence([
        Frame(load_image('cauldron-bubbling'), (-43, -95))
    ], loop),
    'blue': Sequence([
        Frame(load_image('cauldron-bubbling'), (-43, -95))
    ], loop),
    'ready': Sequence([
        Frame(load_image('cauldron-ready'), (-43, -95))
    ], loop),
})


PENTAGRAM_POS = (-128, -66)
PENTAGRAM = Animation({
    'default': Sequence([
        Frame(load_image('pentagram'), PENTAGRAM_POS)
    ], loop),
    'crystals': Sequence([
        Frame(load_image('pentagram-crystals'), PENTAGRAM_POS)
    ], loop),
    'candles': Sequence([
        Frame(load_image('pentagram-candles'), PENTAGRAM_POS)
    ], loop),
    'candles-crystals': Sequence([
        Frame(load_image('pentagram-candles-crystals'), PENTAGRAM_POS)
    ], loop),
    'candles-lit': Sequence([
        Frame(load_image('pentagram-candles-lit'), PENTAGRAM_POS)
    ], loop),
    'ready': Sequence([
        Frame(load_image('pentagram-candles-crystals-lit'), PENTAGRAM_POS)
    ], loop),
})

KNIFE = Animation({
    'default': Sequence(
        load_sequence('knife', 12, (-18, -12)), loop),
})

FONT = (Font('fonts/RosesareFF0000.ttf', 16), False)
BIG_FONT = (Font('fonts/LiberationSerif-Bold.ttf', 100), True)


class FontBubble:
    def __init__(
            self, text,
            pos=(0, 0),
            color=(255, 255, 255),
            anchor='center',
            font=FONT,
            outline=1):
        self.text = text
        self.pos = pos
        self.color = color
        self.anchor = anchor
        self.font = font
        self.outline = outline
        self._build_surf()

    def _build_surf(self):
        font, antialias = self.font
        base = font.render(self.text, antialias, self.color)
        if not self.outline:
            self.surf = base
            return
        black = font.render(self.text, antialias, (0, 0, 0))

        o = self.outline
        o2 = o * 2
        w, h = base.get_size()
        self.surf = pygame.Surface((w + o2, h + o2), pygame.SRCALPHA)

        for off in [(0, 0), (0, o2), (o2, 0), (o2, o2)]:
            self.surf.blit(black, off)

        self.surf.blit(base, (o, o))

    def pos_center(self):
        x, y = self.pos
        w = self.surf.get_width()
        x = min(max(10, x - w // 2), 950 - w)
        return x, y

    def pos_left(self):
        x, y = self.pos
        w = self.surf.get_width()
        x = min(max(10, x), 950 - w)
        return x, y

    @property
    def bounds(self):
        r = self.surf.get_rect()
        r.topleft = self.topleft
        return r

    @property
    def topleft(self):
        return getattr(self, 'pos_' + self.anchor)()

    def draw(self, screen):
        screen.blit(self.surf, self.topleft)


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
        if not self.sprite:
            self.sprite = self.SPRITE.create_instance(pos or self._last_pos)
            self.sprite.dir = 'right'
            self.sprite.play(initial)
        else:
            self.sprite.pos = pos
            self.sprite.dir = dir
            self.sprite.play(initial)

    def hide(self):
        self._last_pos = self.sprite.pos
        self.visible = False
        self.sprite = None

    def _respawn_state(self):
        """Get the scene call needed to respawn the actor."""
        return 'spawn_actor', {
            'name': self.name,
            'pos': self.pos,
            'dir': self.sprite.dir,
            'initial': self.sprite.playing
        }

    @property
    def pos(self):
        return self.sprite.pos

    @pos.setter
    def pos(self, pos):
        if self.sprite:
            self.sprite.pos = pos

    def floor_pos(self):
        return self.pos

    @property
    def z(self):
        """Z-index of actor in scene is related to y-coordinate."""
        return self.sprite.pos[1]

    @property
    def bounds(self):
        return self._bounds.move(*self.sprite.pos)

    def draw(self, screen):
        self.sprite.draw(screen)

    @stage_direction('is at')
    def set_position(self, navpoint='CENTRE STAGE'):
        """Show the character."""
        if isinstance(navpoint, str):
            navpoint = self.scene.navpoints[navpoint]
        if not self.visible:
            self.scene.spawn_actor(self.NAME, navpoint)
        else:
            self.sprite.pos = navpoint

    @stage_direction('is gone')
    def unspawn(self):
        self.scene.unspawn_actor(self)

    def face(self, *args):
        pass

    def on_given(self, item):
        """This actor is given an object."""
        from .inventory import inventory
        actor = self.scene.get_actor('GOBLIT')
        if actor:
            def do_give():
                self.face(actor)
                actor.face(self)
                inventory.remove(item)
            actor.move_to(self.floor_pos(), on_move_end=do_give, strict=False)
        else:
            inventory.remove(item)

    def use_actions(self, item):
        """Get actions for using item with this object."""
        return []

    def click_actions(self):
        return []


class Cauldron(Actor, SceneItem):
    NAME = 'CAULDRON'
    SPRITE = CAULDRON

    _name = None

    @property
    def name(self):
        return self._name or self.NAME

    @name.setter
    def name(self, v):
        self._name = v

    def use_actions(self, item):
        """Get actions for using item with this object."""
        return [
            Action(
                'Add %s to %s' % (item.name, self.name),
                lambda: self.on_given(item)
            )
        ]

    def click_actions(self):
        return [Action('Look at %s' % self.name)]

    def ready(self):
        from .scene import player
        self.sprite.play('ready')
        player.stop_waiting('%s is ready' % self.name)

    @stage_direction('is filled')
    def fill(self):
        self.sprite.play('full')

    blue = False
    bubbling = False

    @stage_direction('turns blue')
    def turn_blue(self):
        self.blue = True
        if self.bubbling:
            self.ready()
        else:
            self.sprite.play('blue')

    @stage_direction('starts bubbling')
    def start_bubbling(self):
        self.bubbling = True
        if self.blue:
            self.ready()
        else:
            self.sprite.play('bubbling')


class Pentagram(Actor, SceneItem):
    NAME = 'PENTAGRAM'
    SPRITE = PENTAGRAM

    _name = None

    @property
    def name(self):
        return self._name or self.NAME

    @name.setter
    def name(self, v):
        self._name = v

    def use_actions(self, item):
        """Get actions for using item with this object."""
        acts = [Action(
            'Put %s onto %s' % (item.name, self.name),
            lambda: self.on_given(item)
        )]
        if self.candles:
            acts.append(
                Action(
                    'Light candles with %s' % (item.name),
                    lambda: self.on_given(item)
                )
            )
        return acts

    def click_actions(self):
        return [Action('Look at %s' % self.name)]

    def ready(self):
        from .scene import player
        self.sprite.play('ready')
        player.stop_waiting('%s is ready' % self.name)

    candles = False
    crystals = False
    lit = False

    def get_sprite(self):
        parts = []
        if self.candles:
            parts.append('candles')
        if self.crystals:
            parts.append('crystals')
        if self.lit:
            parts.append('lit')
        if len(parts) == 3:
            return 'ready'
        elif not parts:
            return 'default'
        return '-'.join(parts)

    def update_sprite(self):
        name = self.get_sprite()
        self.sprite.play(name)
        if name == 'ready':
            self.ready()

    @stage_direction('is lit')
    def fill(self):
        self.lit = True
        self.update_sprite()

    @stage_direction('has candles')
    def add_candles(self):
        self.candles = True
        self.update_sprite()

    @stage_direction('has crystals')
    def add_crystals(self):
        self.crystals = True
        self.update_sprite()


class NPC(Actor):
    def use_actions(self, item):
        """Get actions for using item with this object."""
        return [
            Action(
                'Give %s to %s' % (item.name, self.NAME),
                lambda: self.on_given(item)
            )
        ]

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

    @stage_direction('turns back on')
    def face_away(self, obj):
        if isinstance(obj, tuple):
            pos = obj
        else:
            pos = obj.pos
        px = self.sprite.pos[0]
        if px < pos[0]:
            self.sprite.dir = 'left'
        elif px > pos[0]:
            self.sprite.dir = 'right'
        self.sprite.play('angry')

    @stage_direction('moves to')
    def move_to(self, pos, on_move_end=None, strict=True, exclusive=False):
        if isinstance(pos, str):
            pos = self.scene.get_point_for_name(pos)
        if self.visible and dist(pos, self.pos) > 5:
            self.scene.move(
                self, pos,
                on_move_end=on_move_end,
                strict=strict,
                exclusive=exclusive
            )
        else:
            if on_move_end:
                on_move_end()

    @stage_direction('enters')
    def enter(self, navpoint='ENTRANCE'):
        """Enter via the door and walk to navpoint."""
        pos = self.scene.navpoints['DOOR']
        self.scene.spawn_actor(self.NAME, pos)
        self.move_to(navpoint)

    @stage_direction('is standing by')
    def set_position(self, navpoint='CENTRE STAGE'):
        """Show the character."""
        if not self.visible:
            if isinstance(navpoint, str):
                navpoint = self.scene.navpoints[navpoint]
            self.scene.spawn_actor(self.NAME, navpoint)

    @stage_direction('leaves')
    def leave(self):
        """Walk out of the room."""
        if self.visible:
            self.move_to(
                'DOOR',
                on_move_end=self.unspawn
            )

    @stage_direction('blushes')
    def blush(self):
        self.sprite.play('blushing')

    @stage_direction('is disgusted')
    def disgust(self):
        self.sprite.play('disgusted')

    @stage_direction('is angry')
    def angry(self):
        self.sprite.play('angry')

    @stage_direction('gives')
    def give(self, item):
        from .inventory import inventory
        actor = self.scene.get_actor('GOBLIT')
        if actor:
            def do_give():
                self.face(actor)
                actor.face(self)
                inventory.gain(item)
            self.move_to(actor.floor_pos(), on_move_end=do_give, strict=False)
        else:
            inventory.gain(item)
            raise SCriptError("GOBLIT is not on set to give to")


class Joan(NPC):
    NAME = 'QUEEN JOAN'
    COLOR = (99, 255, 103)
    SPRITE = JOAN


class Goblit(NPC):
    NAME = 'GOBLIT'
    COLOR = (255, 255, 255)
    SPRITE = GOBLIT

    knife = None

    def click_action(self):
        """Clicking on Goblit does nothing."""
        return None

    def use_actions(self, item):
        """Get actions for using item with this object."""
        return [
            Action('Open %s' % item.name),
            Action('Drink %s' % item.name),
            Action('Read %s' % item.name)
        ]

    @stage_direction('looks out of window')
    def look_out_of_window(self):
        self.move_to(
            'WINDOW',
            on_move_end=lambda: self.sprite.play('look-back')
        )

    @stage_direction('fires catapult')
    def do_fire_catapult(self):
        self.sprite.dir = 'right'
        self.sprite.play('catapulting')
        x, y = self.sprite.pos
        ox, oy = 44, -76
        start = (x + ox, y + oy)
        self.knife = KNIFE.create_instance(start)
        from .transitions import MovingSprite
        self.scene.animations.append(
            MovingSprite(
                self.knife, (467, 427 - 390),
                v=500,
                on_move_end=self.do_snip
            )
        )
        return True  # Block, we have to explicitly do_next on the player

    def do_snip(self):
        from .transitions import FallingSprite
        self.scene.set_bg('room-unlit')
        chandelier = self.scene.get('CHANDELIER')
        pentagram = self.scene.get('PENTAGRAM')
        chandelier.z = pentagram.z + 1
        self.chandelier_drop = FallingSprite(chandelier, 0, 0, pentagram.pos[1] - 40, on_move_end=self.finish_chandelier)
        self.scene.animations = [
            FallingSprite(self.knife, 250, 0, self.pos[1], on_move_end=self.finish_snip),
            self.chandelier_drop
        ]

    def finish_snip(self):
        self.scene.spawn_object_on_floor('LETTER OPENER', self.knife.pos)
        self.knife = None
        self.scene.animations = []
        from .scene import player
        player.do_next()

    def finish_chandelier(self):
        self.scene.animations.remove(self.chandelier_drop)
        c = self.scene.get('CHANDELIER')
        p = self.scene.get('PENTAGRAM')
        self.scene.unspawn_object(c)

        x, y = c.pos
        fc = self.scene.spawn_object_near_navpoint('FALLEN CHANDELIER', (x - 20, y + 20), 'CENTRE STAGE')
        fc.z = p.z + 1

    def draw(self, screen):
        if self.knife:
            self.knife.draw(screen)
        self.sprite.draw(screen)


class Tox(NPC):
    NAME = 'WIZARD TOX'
    COLOR = (170, 100, 255)
    SPRITE = TOX

    @stage_direction('turns around')
    def turn_around(self):
        self.sprite.play('sitting')
        self.sprite.dir = 'left'

    @stage_direction('turns back to desk')
    def turn_back_to_desk(self):
        self.sprite.play('sitting-at-desk')
        self.sprite.dir = 'right'


class Amelia(NPC):
    NAME = 'PRINCESS AMELIA'
    COLOR = (255, 220, 100)
    SPRITE = AMELIA


class Ralph(NPC):
    NAME = 'RALPH'
    COLOR = (211, 255, 255)
    SPRITE = RALPH


class Joan(NPC):
    NAME = 'QUEEN JOAN'
    COLOR = (99, 255, 103)
    SPRITE = JOAN
