import sys
import re
import random
from itertools import chain
from functools import wraps, partial
from fnmatch import fnmatchcase as fnmatch
import pygame.mouse
from pygame.cursors import load_xbm

from .loaders import load_image
from .hitmap import HitMap
from .navpoints import points_from_svg
from .routing import Grid
from . import clock
from . import scripts
from .inventory import FloorItem, PointItem, Item, FixedItem
from .transitions import Move
from .geom import dist
from .inventory import inventory
from .actions import Action
from .errors import ScriptError


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
        self._on_animation_finish = set()

    def get_actor(self, name):
        """Get the named actor."""
        a = self.actors.get(name)
        if a in self.objects:
            return a

    def get(self, name):
        """Get the named thing."""
        return (
            self.actors.get(name) or
            self.get_object(name) or
            self.navpoints.get(name) or
            self.hitmap.get_point(name)
        )

    def get_object(self, name):
        for o in self.objects:
            if o.name == name:
                return o

    def __getitem__(self, name):
        """Get the named thing."""
        o = self.get(name)
        if not o:
            raise KeyError(name)

    def _get_state(self):
        scripts = []
        for binding, d in self.object_scripts.items():
            if d:
                scripts.append((True, d.uid))
            else:
                scripts.append((False, binding))
        return {
            'objects': [o._respawn_state() for o in self.objects],
            'object_scripts': scripts
        }

    def _set_state(self, v):
        self.objects = []
        for funcname, params in v['objects']:
            getattr(self, funcname)(**params)

        all_directives = player.binding_directives_seen()
        directives_by_uid = {d.uid: d for d in all_directives}
        directives_by_action = {d.data: d for d in all_directives}
        errors = 0
        for is_bound, uid in v['object_scripts']:
            if not is_bound:
                self.object_scripts[uid] = None
                continue
            try:
                d = directives_by_uid[uid]
            except KeyError:
                errors += 1
                print("Warning: no directive found like", uid)
                try:
                    d = directives_by_action[uid[1]]
                except KeyError:
                    continue
            self.object_scripts[d.data] = d
        if errors:
            print("%s errors: game may not be completeable" % errors)

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

    def spawn_fixed_object_near_navpoint(self, item, pos, navpoint):
        """Spawn an object that can't be picked up.

        pos is the screen position of the object.

        Actors approach the given navpoint to approach the object.

        """
        item = Item.items[item]
        if navpoint not in self.navpoints:
            raise KeyError("Unknown navpoint %s" % navpoint)
        self.objects.append(FixedItem(self, item, pos, navpoint))

    def unspawn_object(self, obj):
        self.objects.remove(obj)

    unspawn_actor = unspawn_object

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

    def get_point_for_name(self, name):
        """Get a floor position for the given name."""
        if name in self.navpoints:
            return self.navpoints[name]

        for o in self.objects:
            if o.name == name:
                return o.floor_pos()

        raise KeyError("Unknown position %s" % name)

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
        self.animations = [a for a in self.animations if a.actor != actor]
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
        self._on_animation_finish.add(callback)

    def _fire_on_animation_finish(self):
        for c in self._on_animation_finish:
            try:
                c()
            except Exception:
                import traceback
                traceback.print_exc()
        self._on_animation_finish.clear()

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

    def find_object_script(self, action_name, wildcards=True):
        """Get an object script for the given action name.

        This will match wildcarded actions also.

        Returns None if no action script is found.

        """
        script = self.object_scripts.get(action_name)
        if script:
            return script
        if wildcards:
            for k, v in self.object_scripts.items():
                if '*' in k:
                    match = fnmatch(action_name, k)
                    if match:
                        return v

    def make_action_handler(self, base_action, wildcards=True):
        """Convert a base action, supplied by an object to a real action.

        Actions are only real actions if there's an allow or deny directive
        for that action. If deny, then the base action is not actually
        done, but any associated script is played.

        """
        if player.waiting == base_action.name:
            base_action.chain(player.stop_waiting)
            return base_action
        script = self.find_object_script(base_action.name, wildcards)
        if script:
            if script.name == 'deny':
                del base_action.callbacks[:]
            base_action.chain(lambda: player.play_subscript(script))
            return base_action
        return None

    HIT_ACTIONS = [
        'Look at %s',
        'Look out of %s'
    ]

    def get_objects(self, pos):
        """Iterate over all objects under the given point."""
        for o in self.objects:
            if o.bounds.collidepoint(pos):
                yield o

    def collidepoint(self, pos):
        """Iterate over all object names under the given point."""
        yield from (o.name for o in self.get_objects(pos))

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
        """Find an action for using the two named items together.

        """
        for template, canonical in self.WILDCARD_ACTIONS:
            base_action = Action(
                template.format(item=name, target=other_name)
            )
            action = self.make_action_handler(base_action, wildcards=False)
            if action:
                action.name = canonical.format(
                    item=name, target=other_name
                )
                return action

    def action_item_use(self, item, pos):
        """Find an action for using the item with the given screen position.

        If the item supports use_actions with the given item, they will be
        used if there's a handler bound. Otherwise we fall back to the
        click action.

        """
        # FIXME: wildcarded actions should always come below specific actions.
        # Might have to do multiple passes over the objects, first looking for
        # specific matches, then wildcards.
        for o in self.get_objects(pos):
            object_actions = chain(o.use_actions(item), o.click_actions())
            for base_action in object_actions:
                action = self.make_action_handler(base_action)
                if action:
                    return action

        region = self.hitmap.region_for_point(pos)
        if region:
            return self.action_item_together(item.name, region)

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


class DialogueChoice:
    def __init__(self, player, directive):
        self.player = player
        for d in directive.contents:
            if not isinstance(d, scripts.Directive) or d.name != 'choice':
                raise ScriptError(
                    "Children of choose-any directives must be choice "
                    "directives"
                )
        self.directive = directive
        self._build()

    @property
    def choices(self):
        return self.directive.contents

    def _build(self):
        from .actors import FontBubble
        self.bubbles = []
        for i, d in enumerate(self.choices):
            bubble = FontBubble(d.data, (40, 460 + 40 * i), color=(255, 240, 180), anchor='left')
            self.bubbles.append(bubble)

    def for_point(self, pos):
        for directive, bubble in zip(self.choices, self.bubbles):
            if bubble.bounds.collidepoint(pos):
                return Action(directive.data, partial(self.choose, directive))

    def choose(self, script):
        self.player.dialogue_choice = None
        self.player.play_subscript(script)

    def draw(self, screen):
        for b in self.bubbles:
            b.draw(screen)


class AllDialogueChoice(DialogueChoice):
    def choose(self, script):
        self.choices.remove(script)
        if not self.choices:
            self.player.dialogue_choice = None
        else:
            self._build()
        self.player.play_subscript(script)


class ScriptPlayer:
    @classmethod
    def from_file(cls, name, clock=clock, on_finish=None):
        s = scripts.parse_file(name)
        return cls(s, clock, on_finish)

    def __init__(self, script, clock, on_finish=None):
        self.clock = clock
        self.stack = []
        self.skippable = False  # If we can safely skip the delay
        self.finished = False
        self.fast_forward = False
        self.need_save = False
        self.on_finish = on_finish
        self.play_subscript(script)

    def _get_state(self):
        """Get the waiting state."""
        if len(self.stack) > 1:
            raise ValueError("Can't save at this time, have subscripts")
        if not self.waiting and not self.need_save:
            raise ValueError("Can't save at this time, no puzzle to solve")
        return self.need_save or self._waiting, self.solved

    def _set_state(self, v):
        """Skip forward to the step we were waiting for."""
        waiting, solved = v
        self.fast_forward = True
        while not self.finished:
            if self._waiting == waiting:
                self.need_save = False
                if solved:
                    self.waiting = None
                    self.do_next()
                self.fast_forward = False
                break
            self.skip(force=True)
        else:
            self.fast_forward = False
            self.need_save = False
            raise KeyError("Couldn't resume script.")

    def save(self, solved=False):
        if not self.fast_forward:
            self.solved = solved
            save_game()
        self.need_save = False

    @property
    def root_script(self):
        return self.stack[0][0]

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
    def _waiting(self):
        return self.stack[-1][2]

    @_waiting.setter
    def _waiting(self, v):
        self.stack[-1][2] = v

    @property
    def waiting(self):
        if self._waiting is None:
            return None
        return self._waiting[0]

    @waiting.setter
    def waiting(self, v):
        if v is None:
            self._waiting = v
        else:
            self._waiting = v, 0

    @property
    def dialogue_choice(self):
        return self.stack[-1][3]

    @dialogue_choice.setter
    def dialogue_choice(self, v):
        self.stack[-1][3] = v

    def is_interactive(self):
        """Return True if we're in interactive mode.
        """
        return bool(self.waiting or self.dialogue_choice)

    def show_inventory(self):
        """Should the inventory panel be drawn.

        We want to draw it unless there are dialog choices.

        """
        return not self.dialogue_choice

    def play_subscript(self, script):
        if self.need_save:
            self.save(solved=True)
        self.stack.append([script, 0, None, None])
        if scene.animations:
            scene.on_animation_finish(self.next)
        else:
            self.next()

    def end_subscript(self):
        self.stack.pop()
        if self.dialogue_choice:
            if len(self.dialogue_choice.choices) == 1:
                self.dialogue_choice.choose(self.dialogue_choice.choices[0])
        elif not self.waiting:
            self.do_next()

    def next(self):
        if self.need_save:
            self.save(solved=True)
        if self.step >= len(self.script.contents):
            if len(self.stack) > 1:
                self.end_subscript()
            else:
                self.finished = True
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

    def skip(self, force=False):
        if force and self.dialogue_choice:
            self.dialogue_choice = None

        if force or self.skippable and not self.waiting:
            self.clock.unschedule(self.cancel_line)
            self.clock.unschedule(self.next)
            scene.close_bubble()
            if scene.animations:
                scene.skip_animation()
            else:
                self.next()

    def skip_all(self):
        while self.skippable and not self.waiting and not self.finished:
            self.skip()

    def stop_waiting(self):
        if self.waiting:
            self.need_save = self._waiting
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

    def walk_script(self, script=None):
        """Iterate over every directive in the script."""
        if script is None:
            script = self.root_script.contents
        for s in script:
            if isinstance(s, scripts.Directive):
                yield s
                yield from self.walk_script(s.contents)

    def script_so_far(self):
        pos = self.stack[0][1]
        return self.root_script.contents[:pos]

    def binding_directives_seen(self):
        """Return a list of event binding directives in the script so far."""
        prev_directives = self.walk_script(self.script_so_far())
        return [d for d in prev_directives if d.name in ('allow', 'deny')]

    def do_line(self, line):
        scene.say(line.character, line.line)
        self.clock.schedule(self.cancel_line, 3)
        self.skippable = True

    def do_pause(self, pause):
        self.schedule_next()
        self.skippable = True

    def do_action(self, action):
        self._waiting = action.verb, action.uid
        self.save(solved=False)

    def base_do_stagedirection(self, d):
        actor = scene.get_actor(d.character)
        if not actor:
            if d.verb in ('enters', 'is gone', 'appears', 'is standing by'):
                actor = scene.actors[d.character]
            else:
                raise ScriptError("Actor %s is not on set" % d.character)
        handler = actor.stage_directions.get(d.verb)
        if not handler:
            raise ScriptError(
                "Unsupported stage direction %r for %s" % (d.verb, d.character)
            )
        if d.object:
            if d.verb == 'gives':
                # Items are given, not scene objects
                handler(actor, d.object)
            else:
                object = scene.get(d.object)
                if not object:
                    raise ScriptError("%s is not on set" % d.object)
                handler(actor, object)
        else:
            handler(actor)

    def do_stagedirection(self, d):
        self.base_do_stagedirection(d)
        self.do_next()

    def do_multistagedirection(self, d):
        for direction in d.directions:
            self.base_do_stagedirection(direction)
        self.do_next()

    def do_directive(self, directive):
        name = directive.name
        handler = getattr(self, 'directive_' + name.replace('-', '_'), None)
        if not handler:
            raise ScriptError("No handler for directive %s" % name)
        handler(directive)

    @simple_directive
    def directive_destroy(self, directive):
        """Destroy an object."""
        name = directive.data
        obj = scene.get(name)
        if obj:
            scene.unspawn_object(obj)

    def directive_allow(self, directive):
        scene.object_scripts[directive.data] = directive
        self.do_next()

    directive_deny = directive_allow

    @simple_directive
    def directive_unbind(self, directive):
        scene.object_scripts[directive.data] = None

    @simple_directive
    def directive_rename(self, directive):
        mo = re.match(r'^([A-Z ]+?)\s*->\s*([A-Z ]+)$', directive.data)
        if not mo:
            raise ScriptError("Couldn't parse rename directive %r" % directive.data)
        try:
            scene.rename(*mo.groups())
        except KeyError as e:
            raise ScriptError("No such object %r" % e.args[0])

    @simple_directive
    def directive_gain(self, directive):
        """Gain an item."""
        try:
            inventory.gain(directive.data)
        except KeyError:
            raise ScriptError("No such item %s" % directive.data)

    @simple_directive
    def directive_craft(self, directive):
        """Craft an item from others."""
        mo = re.match(r'^([A-Z +]+?)\s*->\s*([A-Z +]+)$', directive.data)
        if not mo:
            raise ScriptError(
                "Couldn't parse craft directive %r" % directive.data)

        inputs, outputs = (
            [item.strip() for item in g.split('+') if item.strip()]
            for g in mo.groups()
        )
        if not inputs:
            raise ScriptError(
                "No inputs for craft directive %r" % directive.data)
        if not outputs:
            raise ScriptError(
                "No outputs for craft directive %r" % directive.data)
        for i in inputs:
            try:
                inventory.lose(i)
            except ValueError:
                raise ScriptError("Player does not have %s" % i)
        for o in outputs:
            inventory.gain(o)

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

    def choose_dialogue(self, script):
        self.dialogue_choice = None

    def directive_choose_any(self, directive):
        self.dialogue_choice = DialogueChoice(self, directive)

    def directive_choose_all(self, directive):
        self.dialogue_choice = AllDialogueChoice(self, directive)


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
    if len(sys.argv) == 2:
        load_savegame(sys.argv[1])
    else:
        load_savegame()


def on_mouse_down(pos, button):
    if button == 3 and player.skippable:
        player.skip()
        return

    if button == 1 and player.is_interactive():
        if player.dialogue_choice:
            action = player.dialogue_choice.for_point(pos)
            if action:
                action()
        elif inventory.selected:
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

    if not player.is_interactive():
        return

    if player.dialogue_choice:
        action = player.dialogue_choice.for_point(pos)
        if action:
            Cursor.set_pointer()
        else:
            Cursor.set_default()
    elif inventory.selected:
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


def get_saves():
    import os
    if not os.path.exists('saves'):
        return

    for p in os.listdir('saves'):
        mo = re.match('^save-(\d+).pck$', p)
        if mo:
            yield p, int(mo.group(1))


def save_game(solved=True):
    import re
    import os
    import pickle
    save_data = {
        'inventory': inventory.__getstate__(),
        'player': player._get_state(),
        'scene': scene._get_state()
    }

    try:
        os.mkdir('saves')
    except IOError:
        pass
    try:
        last_save = max(num for path, num in get_saves())
    except ValueError:
        next_save = 1
    else:
        next_save = last_save + 1
    save_path = os.path.join('saves', 'save-%d.pck' % next_save)
    with open(save_path, 'wb') as f:
        pickle.dump(save_data, f, -1)


def load_savegame(filename=None):
    global scene, player, inventory

    import os
    import pickle

    if not filename:
        try:
            last_save = max(get_saves(), key=lambda s: s[1])[0]
        except ValueError:
            # No save data
            return

        filename = os.path.join('saves', last_save)

    print("Loading", filename)

    try:
        f = open(filename, 'rb')
    except (IOError, OSError) as e:
        # No save data
        return

    with f:
        save_data = pickle.load(f)

    player_state = save_data['player']
    try:
        player._set_state(player_state)
    except ValueError as e:
        print("Failed to restore script player state:", e.args[0])
        return

    from . import inventory as inv
    scene._set_state(save_data['scene'])
    inventory.__setstate__(save_data['inventory'])
    return True


def draw(screen):
    scene.draw(screen)
    if player.dialogue_choice:
        player.dialogue_choice.draw(screen)
    elif player.show_inventory():
        inventory.draw(screen)

#   Uncomment to enable debugging of routing
#    g = scene.grid.build_npcs_grid([a.pos for a in scene.actors.values()])
#    screen.blit(g.surf, (0, 0))
