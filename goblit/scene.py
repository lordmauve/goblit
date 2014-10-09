import pygame.mouse
from pygame.cursors import load_xbm

from .loaders import load_image
from .hitmap import HitMap
from .navpoints import points_from_svg
from .routing import Grid
from . import clock
from . import scripts
from .inventory import FloorItem
from .transitions import Move
from .geom import dist
from .inventory import inventory
from .actions import Action


TITLE = 'The Legend of Goblit'
ICON = 'data/icon.png'


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
        a = self.actors.get(name)
        if a in self.objects:
            return a

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
        from .actors import ACTORS
        self.actors = {cls.NAME: cls(self) for cls in ACTORS}

    def init_scene(self):
        self.spawn_actor('WIZARD TOX', (719, 339), initial='sitting-at-desk')
        from . import items
        items.spawn_all(self)
        clock.each_tick(self.update)

    def spawn_actor(self, name, pos=None, dir='right', initial='default'):
        actor = self.actors[name]
        actor.show(pos, dir, initial)
        self.objects.append(actor)

    def hide_actor(self, name):
        actor = self.actors[name]
        actor.hide()
        self.objects.remove(actor)

    def spawn_object_on_floor(self, item, pos):
        self.objects.append(FloorItem(self, item, pos))

    def unspawn_object(self, obj):
        self.objects.remove(obj)

    def nearest_navpoint(self, pos):
        """Get the position of the nearest navpoint to pos."""
        return min(self.navpoints.values(), key=lambda p: dist(p, pos))

    def say(self, actor_name, text):
        from .actors import SpeechBubble
        actor = self.get_actor(actor_name)
        if not actor:
            raise ScriptError("No such actor %s" % actor_name)
        if not actor.visible:
            raise ScriptError("Actor %s is not on set" % actor_name)
        self.bubble = SpeechBubble(text, actor)
        if actor_name != 'GOBLIT':
            goblit = self.get_actor('GOBLIT')
            if goblit:
                goblit.face(actor)

    def action_text(self, msg):
        from .actors import FontBubble
        self.bubble = FontBubble(msg, pos=(480, 435))

    def close_bubble(self):
        self.bubble = None

    def move(self, actor, goal, on_move_end=None, strict=True, exclusive=False):
        npcs = [a.pos for a in self.actors.values() if a != actor]
        if exclusive:
            npcs.append(goal)
        route = self.grid.route(actor.pos, goal, npcs=npcs, strict=strict)
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

        self.objects.sort(key=lambda o: o.z)
        for o in self.objects:
            o.draw(screen)
        screen.blit(self.room_fg, (0, 0))

        if self.bubble:
            self.bubble.draw(screen)

    def get_action_handler(self, action):
        """Get an additional scripted action for the given action name."""
        script = scene.object_scripts.get(action)
        if script:
            return lambda: player.play_subscript(script)
        if player.waiting == action:
            return player.stop_waiting
        return None

    def get_action(self, action):
        handler = self.get_action_handler(action)
        if handler:
            return Action(action, handler)

    HIT_ACTIONS = [
        'Look at %s',
        'Look out of %s',
    ]

    def collidepoint(self, pos):
        """Iterate over all object under the given point."""
        for o in self.objects:
            if o.bounds.collidepoint(pos):
                yield o.name

        r = self.hitmap.region_for_point(pos)
        if r:
            yield r

    def iter_actions(self, pos):
        """Iterate over all possible actions for the given point."""
        for o in self.objects:
            if o.bounds.collidepoint(pos):
                for a in o.click_actions():
                    yield a

        r = self.hitmap.region_for_point(pos)
        if r:
            for a in self.HIT_ACTIONS:
                yield Action(a % r, lambda: scene.get_actor('GOBLIT').face(pos))

    def action_item_use(self, item, pos):
        for objname in self.collidepoint(pos):
            item_action = item.get_use_action(objname)
            if item_action:
                handler = self.get_action_handler(item_action.name)
                if handler:
                    item_action.chain(handler)
                return item_action
            else:
                default_name = 'Use %s with %s' % (item.name, objname)
                action = self.get_action(default_name)
                if action:
                    return action
                action = self.get_action('Use * with *')
                if action:
                    action.name = default_name
                    return action

    def action_click(self, pos):
        """Get an action for the given point."""
        for action in self.iter_actions(pos):
            handler = self.get_action_handler(action.name)
            if handler:
                action.chain(handler)
                return action


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
    @classmethod
    def from_file(cls, name, clock=clock, on_finish=None):
        s = scripts.parse_file('script')
        return cls(s, clock, on_finish)

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

    def is_interactive(self):
        """Return True if we're in interactive mode.
        """
        return bool(self.waiting)

    def show_inventory(self):
        """Should the inventory panel be drawn.

        We want to draw it unless there are dialog choices.

        """
        return True

    def play_subscript(self, script):
        self.stack.append([script, 0, None])
        if scene.animations:
            scene.on_animation_finish(self.next)
        else:
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
        if self.skippable and not self.waiting:
            self.clock.unschedule(self.cancel_line)
            self.clock.unschedule(self.next)
            scene.close_bubble()
            if scene.animations:
                scene.skip_animation()
            else:
                self.next()

    def skip_all(self):
        while self.skippable and not self.waiting:
            self.skip()

    def stop_waiting(self):
        if self.waiting:
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
        self.waiting = action.verb

    def do_stagedirection(self, d):
        actor = scene.get_actor(d.character)
        if not actor:
            if d.verb == 'enters':
                actor = scene.actors[d.character]
            else:
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

    def directive_on(self, directive):
        scene.object_scripts[directive.data.strip()] = directive
        self.do_next()

    def directive_include(self, directive):
        if directive.contents:
            raise ScriptError("Include directive may not have contents.")
        filename = directive.data.strip()
        s = scripts.parse_file(filename)
        self.play_subscript(s)


# Script player
player = None
scene = None


def load():
    global player, scene
    scene = Scene()
    scene.load()
    Cursor.load()

    player = ScriptPlayer.from_file('script')

    scene.init_scene()


def on_mouse_down(pos, button):
    if button == 3 and player.skippable:
        player.skip()
        return

    if button == 1 and player.is_interactive():
        if inventory.selected:
            action = scene.action_item_use(inventory.selected, pos)
            if action:
                inventory.deselect()
                Cursor.set_pointer()
                action()
        else:
            r = scene.action_click(pos)
            if r:
                r()
                Cursor.set_default()
            else:
                if player.show_inventory():
                    item = inventory.item_for_pos(pos)
                    if item:
                        inventory.select(item)
                        return
                goblit = scene.get_actor('GOBLIT')
                if goblit:
                    try:
                        goblit.move_to(pos)
                    except ValueError:
                        pass
            inventory.deselect()


def on_mouse_move(pos, rel, buttons):
    global bubble

    if not player.waiting:
        return

    if inventory.selected:
        action = scene.action_item_use(inventory.selected, pos)
        if action:
            Cursor.set_pointer()
            scene.action_text(action.name)
        else:
            scene.action_text('Use %s' % inventory.selected.name)
    else:
        action = scene.action_click(pos)
        if action:
            Cursor.set_pointer()
            scene.action_text(action.name)
        else:
            if player.show_inventory():
                item = inventory.item_for_pos(pos)
                if item:
                    Cursor.set_pointer()
                    scene.action_text(item.name)
                    return
            Cursor.set_default()
            scene.close_bubble()


def on_key_down(unicode, key, mod, scancode):
    if key == pygame.K_ESCAPE:
        player.skip_all()


def update(dt):
    clock.tick(dt)


def draw(screen):
    scene.draw(screen)
    if player.show_inventory():
        inventory.draw(screen)

#   Uncomment to enable debugging of routing
#    g = scene.grid.build_npcs_grid([a.pos for a in scene.actors.values()])
#    screen.blit(g.surf, (0, 0))
