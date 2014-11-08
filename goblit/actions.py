from itertools import chain
from functools import partial
from .errors import ScriptError
from .transitions import Move


def do_all(*callbacks):
    """Return a function that will call all the given functions."""
    def go():
        for c in callbacks:
            try:
                c()
            except Exception:
                import traceback
                traceback.print_exc()
    return go


class Action:
    """An action the player can take."""
    def __init__(self, name, callback=None):
        self.name = name
        self.callbacks = [callback] if callback else []

    def __call__(self):
        for c in self.callbacks:
            try:
                c()
            except Exception:
                import traceback
                traceback.print_exc()

    def chain(self, handler):
        """Call another handler after this one."""
        self.callbacks.append(handler)


class SceneAction:
    """Abstract base class for things that happen in the scene."""

    # A callback to be called when the action completes
    # This is used for chaining and should not be overridden.
    on_finish = None

    def play(self, scene):
        """Subclasses should implement this to play the animation."""

    def done(self):
        """Called by play() to indicate the action has finished."""
        if self.on_finish:
            self.on_finish()

    def error(self, msg):
        """Shortcut for raising a ScriptError.

        msg will be formatted using format() semantics, with all instance
        attributes available for substitution.

        For example, if the instance has an attribute 'actor_name', then
        you could raise a ScriptError with the call:

            self.error('No such actor {actor_name}')

        """
        m = msg.format(**vars(self))
        raise ScriptError(m)

    def __rshift__(self, ano):
        return ActionChain(self, ano)

    def __add__(self, ano):
        return ParallelAction(self, ano)


class BaseMultiAction(SceneAction):
    """Abstract base class for classes that run a number of actions."""
    def __init__(self, *actions):
        self.actions = actions

        for a in self.actions:
            a.on_finish = partial(self.on_finish, a)

        if self._can_skip():
            self.skip = self._skip

    def _can_skip(self):
        return all(hasattr(a, 'skip') for a in self.actions)


class ActionChain(BaseMultiAction):
    """A sequence of actions.

    Each action will be played sequentially, then on_finish will be called.

    """

    def play(self, scene):
        self.current = -1
        self.scene = scene
        self.next()

    def on_finish(self, a):
        self.next()

    def _skip(self, scene):
        """Skip all actions that have not yet been completed."""
        for a in self.actions[self.current:]:
            a.skip(scene)

    def next(self):
        """Trigger the next action."""
        if self.current >= len(self.actions) - 1:
            self.done()
            return

        self.current += 1
        action = self.actions[self.current]
        action.play(self.scene)

    def __rshift__(self, ano):
        return ActionChain(*chain(self.actions, [ano]))


class ParallelAction(BaseMultiAction):
    """Play a number of actions in parallel."""
    def play(self, scene):
        self.waiting = set(self.actions)
        for a in self.actions:
            a.play(scene)

    def _skip(self, scene):
        """Skip all actions that have not yet been completed."""
        for a in self.waiting:
            a.skip(scene)

    def on_finish(self, action):
        """Stop waiting for the given action.

        If no actions left to wait for, we're done.

        """
        self.waiting.remove(action)
        if not self.waiting:
            self.done()

    def __add__(self, ano):
        """Extend a Parallel rather than nesting more deeply."""
        return ParallelAction(*chain(self.actions, [ano]))


class Generic(SceneAction):
    """A generic action.

    This is useful for chaining an arbitrary piece of (synchronous) code into
    an action sequence.

    """
    def __init__(self, callback):
        self.callback = callback

    def play(self, scene):
        try:
            self.callback()
        finally:
            self.done()

    def skip(self, scene):
        self.callback()


class MoveTo(SceneAction):
    """Move an actor to a point.

    The point can be specified as a name (referring to a named point, actor
    or item), or as an (x, y) tuple.

    """
    def __init__(self, actor, goal, strict=False, exclusive=False):
        self.actor = actor
        self.goal = goal
        self.strict = strict
        self.exclusive = exclusive
        self.transition = None

    def lookup(self, scene):
        """Get actor and destination position"""
        a = scene.get_actor(self.actor)
        pos = scene.lookup_position(self.goal)
        return a, pos

    def play(self, scene):
        self.scene = scene
        a, pos = self.lookup(scene)
        if a:
            route = scene.get_route(
                a,
                pos,
                strict=self.strict,
                exclusive=self.exclusive
            )
            self.transition = Move(route, a, on_move_end=self.on_move_end)
            self.update = self.transition.update
            self.scene.clock.each_tick(self.update)
        else:
            self.transition = None
            raise ScriptError("%s is not on set to move" % self.actor)

    def cancel(self):
        """Stop moving right where we are.

        Called by the scene when being replaced by a new move animation.

        """
        if self.transition:
            self.scene.clock.unschedule(self.update)

    def skip(self, scene):
        if self.transition:
            self.transition.on_move_end = None
            self.transition.skip()
            self.scene.clock.unschedule(self.update)
        else:
            a, pos = self.lookup(scene)
            a.pos = pos

    def on_move_end(self):
        self.scene.clock.unschedule(self.update)
        self.done()


class PCMoveTo(MoveTo):
    """Move the player character to a point.

    The point can be specified as a named point or an (x, y) tuple.

    """
    def __init__(self, goal, strict=False, exclusive=False):
        self.goal = goal
        self.strict = strict
        self.exclusive = exclusive

    def play(self, scene):
        self.actor = scene.pc_name
        super().play(scene)


class Say(SceneAction):
    """Have an actor say a line."""
    def __init__(self, actor, line):
        self.actor = actor
        self.line = line

    def estimate_line_time(self):
        words = self.line.split()
        return 1.0 + 0.2 * len(words) + 0.01 * len(self.line)

    def play(self, scene):
        self.scene = scene
        scene.say(self.actor, self.line)
        t = self.estimate_line_time()
        scene.clock.schedule(self.cancel_line, t)

    def skip(self, scene):
        self.scene.clock.unschedule(self.cancel_line)
        self.scene.close_bubble()

    def cancel_line(self):
        self.scene.close_bubble()
        self.done()


class Pause(SceneAction):
    """Pause for a moment, before action continues."""
    def __init__(self, delay=1):
        self.delay = delay

    def play(self, scene):
        scene.clock.schedule(self.done, self.delay)

    def skip(self, scene):
        scene.clock.unschedule(self.done)


class Synchronous(SceneAction):
    """Abstract base class for actions that don't cause a delay.

    Subclasses should implement do() to perform the action.

    """
    def play(self, scene):
        self.do(scene)
        self.done()

    def skip(self, scene):
        self.do(scene)


class Spawn(Synchronous):
    """Spawn an actor at a specific point."""
    def __init__(self, actor_name, pos):
        self.actor_name = actor_name
        self.pos = pos

    def do(self, scene):
        p = scene.navpoints[self.pos]
        scene.spawn_actor(self.actor_name, p)


class Unspawn(Synchronous):
    """Unspawn an actor."""
    def __init__(self, actor_name):
        self.actor_name = actor_name

    def do(self, scene):
        scene.unspawn_actor(self.actor_name)


class SetPosition(Synchronous):
    """Set the position of an actor"""
    def __init__(self, actor_name, pos):
        self.actor_name = actor_name
        self.pos = pos

    def do(self, scene):
        p = scene.navpoints[self.pos]
        a = scene.get_actor(self.actor_name)
        if a:
            a.pos = p
        else:
            scene.spawn_actor(self.actor_name, p)


class Play(Synchronous):
    """Play an animation."""
    def __init__(self, actor_name, animation):
        self.actor_name = actor_name
        self.animation = animation

    def do(self, scene):
        a = scene.get_actor(self.actor_name)
        if not a:
            self.error('{actor_name} is not on set to play "{animation}"')
        if self.animation not in a.sprite.SEQUENCES:
            self.error('{actor_name} does not support animation "{animation}"')
        a.sprite.play(self.animation)


class Face(Synchronous):
    """Turn to face a location or object."""
    def __init__(self, actor_name, target):
        self.actor_name = actor_name
        self.target = target

    def do(self, scene):
        pos = scene.lookup_position(self.target)
        if not pos:
            self.error('No such position/object {target}')
        a = self.scene.get_actor(self.actor_name)
        if not a:
            self.error('{actor_name} is not on set to turn')
        self.do_turn(a, pos)

    def do_turn(self, a, pos):
        a.face(pos)


class FaceAway(Face):
    """Turn away from a location or object."""
    def do_turn(self, a, pos):
        a.face_away(pos)


class FaceLeft(Synchronous):
    """Make an actor face left."""
    def __init__(self, actor_name):
        self.actor_name = actor_name

    def do(self, scene):
        a = self.scene.get_actor(self.actor_name)
        if not a:
            self.error('{actor_name} is not on set to turn')
        self.do_turn(a)

    def do_turn(self, a):
        a.sprite.dir = 'left'


class FaceRight(FaceLeft):
    """Make an actor face right."""
    def do_turn(self, a):
        a.sprite.dir = 'right'


class SetBackground(Synchronous):
    """Set the scene background."""
    def __init__(self, background_name):
        self.background_name = background_name

    def do(self, scene):
        scene.set_bg(self.background_name)


class Gain(Synchronous):
    """Gain an inventory item."""
    def __init__(self, item_name):
        self.item_name = item_name

    def do(self, scene):
        from .inventory import inventory
        inventory.gain(self.item_name)


class Lose(Gain):
    """Lose an inventory item."""
    def do(self, scene):
        from .inventory import inventory
        inventory.lose(self.item_name)
