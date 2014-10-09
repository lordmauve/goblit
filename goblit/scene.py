import re
import random
from functools import wraps
import pygame.mouse
from pygame.cursors import load_xbm

from .loaders import load_image
from .hitmap import HitMap
from .navpoints import points_from_svg
from .routing import Grid
from . import clock
from . import scripts
from .inventory import FloorItem, PointItem, Item
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
        """Spawn an object that is not on the floor.

        pos is both the screen position and the inferred position on the floor.

        """
        item = Item.items[item]
        self.objects.append(FloorItem(self, item, pos))

    def spawn_object_near_navpoint(self, item, pos, navpoint):
        """Spawn an object.

        pos is the screen position of the object.

        Actors approach the given navpoint to approach the object.

        """
        item = Item.items[item]
        if navpoint not in self.navpoints:
            raise KeyError("Unknown navpoint %s" % navpoint)
        self.objects.append(PointItem(self, item, pos, navpoint))

    def unspawn_object(self, obj):
        self.objects.remove(obj)

    def rename(self, current_name, new_name):
        """Rename an object or hit area."""
        for o in self.objects:
            if o.name == current_name:
                o.name = new_name
                return

        hitmap = self.hitmap.regions
        for k, v in hitmap.items():
            if k == current_name:
                del hitmap[k]
                hitmap[new_name] = v
                return

        raise KeyError(current_name)

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
        npcs = [a.pos for a in self.actors.values() if a != actor and a.visible]
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

    def make_action_handler(self, base_action):
        """Convert a base action, supplied by an object to a real action.

        Actions are only real actions if there's an allow or deny directive
        for that action. If deny, then the base action is not actually
        done, but any associated script is played.

        """
        if player.waiting == base_action.name:
            base_action.chain(player.stop_waiting)
            return base_action
        script = scene.object_scripts.get(base_action.name)
        if script:
            if script.name == 'deny':
                del base_action.callbacks[:]
            base_action.chain(lambda: player.play_subscript(script))
            return base_action
        return None

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

    USE = 'Use {item} with {target}'
    GIVE = 'Give {item} to {target}'
    WILDCARD_ACTIONS = [
        (USE, USE),
        ('Use {target} with {item}', USE),
        ('Give {item} to {target}', GIVE),
        ('Give * to {target}', GIVE),
        ('Use {item} with *', USE),
        ('Use * with {target}', USE),
        ('Use * with *', USE),
    ]

    def action_item_together(self, name, other_name):
        """Find an action for using the two named items together."""
        for template, canonical in self.WILDCARD_ACTIONS:
            base_action = Action(
                template.format(item=name, target=other_name)
            )
            action = self.make_action_handler(base_action)
            if action:
                action.name = canonical.format(
                    item=name, target=other_name
                )
                return action

    def action_item_use(self, item, pos):
        """Find an action for using the item with the given screen position."""
        # FIXME: If the other object is an object in the scene, make sure
        # Goblit has picked up the thing first. Only the kettle doesn't get
        # picked up, right?
        for objname in self.collidepoint(pos):
            item_action = item.get_use_action(objname)
            if item_action:
                return self.make_action_handler(item_action)
            else:
                action = self.action_item_together(item.name, objname)
                if action:
                    return action

    def action_click(self, pos):
        """Get an action for the given point."""
        for action in self.iter_actions(pos):
            handler = self.make_action_handler(action)
            if handler:
                return handler


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


def simple_directive(func):
    """Shortcut for simple directives.

    Define a directive that doesn't take contents and which completes
    immediately.

    """
    @wraps(func)
    def _wrapper(self, directive):
        if directive.contents:
            raise ScriptError(
                "%s directive may not have contents." % directive.name
            )
        func(self, directive)
        self.do_next()
    return _wrapper


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
        self.skippable = True
        if scene.animations:
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

    def directive_allow(self, directive):
        scene.object_scripts[directive.data.strip()] = directive
        self.do_next()

    directive_deny = directive_allow

    @simple_directive
    def directive_unbind(self, directive):
        del scene.object_scripts[directive.data.strip()]

    def directive_include(self, directive):
        if directive.contents:
            raise ScriptError("Include directive may not have contents.")
        filename = directive.data
        s = scripts.parse_file(filename)
        self.skippable = True
        self.play_subscript(s)

    @simple_directive
    def directive_rename(self, directive):
        mo = re.match(r'^([A-Z ]+?)\s*->\s*([A-Z ]+)$', directive.data)
        if not mo:
            raise ScriptError("Couldn't parse rename directive %r" % directive.data)
        scene.rename(*mo.groups())

    @simple_directive
    def directive_gain(self, directive):
        """Gain an item."""
        try:
            inventory.gain(directive.data)
        except KeyError:
            raise ScriptError("No such item %s" % directive.data)

    @simple_directive
    def directive_lose(self, directive):
        """Lose an item."""
        try:
            inventory.lose(directive.data)
        except KeyError:
            raise ScriptError("No such item %s" % directive.data)
        except ValueError:
            raise ScriptError("Player does not have %s" % directive.data)

    def directive_choice(self, directive):
        """On its own, does nothing. Just plays the contents.

        Useful for grouping.

        """
        self.play_subscript(directive)

    def directive_random(self, directive):
        """Pick one contents line at random.

        For example,

        .. random::

            GOBLIT: Maybe I'll say this.
            GOBLIT: Maybe I'll say that.
            .. choice::
                GOBLIT: Maybe I'll say this...
                GOBLIT: ...then that.

        """
        s = scripts.Script([random.choice(directive.contents)])
        self.skippable = True
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
            elif player.show_inventory():
                item = inventory.item_for_pos(pos)
                if item:
                    if item is inventory.selected:
                        inventory.select(item)
                        return

                    Cursor.set_pointer()
                    action = scene.action_item_together(inventory.selected.name, item.name)
                    if action:
                        action()
                    inventory.deselect()
                    return
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
            if player.show_inventory():
                item = inventory.item_for_pos(pos)
                if item:
                    if item is inventory.selected:
                        scene.action_text(item.name)
                        return

                    Cursor.set_pointer()
                    scene.action_text(
                        'Use %s with %s' % (inventory.selected.name, item.name)
                    )
                    return

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
