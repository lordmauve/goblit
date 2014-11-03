from itertools import chain
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

    def __add__(self, ano):
        return ActionChain(self, ano)


class ActionChain(SceneAction):
    """A sequence of actions.

    Each action will be played sequentially, then on_finish will be called.

    """
    def __init__(self, *actions):
        self.actions = actions

        for a in self.actions:
            a.on_finish = self.next

        if self._can_skip():
            self.skip = self._skip

    def _can_skip(self):
        return all(hasattr(a, 'skip') for a in self.actions)

    def _skip(self):
        """Skip all actions that have not yet been started."""
        for a in self.actions[self.current:]:
            a.skip()

    def play(self, scene):
        self.current = -1
        self.scene = scene
        self.next()

    def next(self):
        if self.current >= len(self.actions) - 1:
            self.done()
            return

        self.current += 1
        action = self.actions[self.current]
        action.on_finish = self.next
        action.play(self.scene)

    def __add__(self, ano):
        return ActionChain(*chain(self.actions, [ano]))


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

    def skip(self):
        self.callback()


class MoveTo(SceneAction):
    """Move an actor to a point.

    The point can be specified as a named point or an (x, y) tuple.

    """
    def __init__(self, actor, goal, strict=False, exclusive=False):
        self.actor = actor
        self.goal = goal
        self.strict = strict
        self.exclusive = exclusive

    def play(self, scene):
        self.scene = scene
        a = scene.get_actor(self.actor)
        if a:
            route = scene.get_route(
                a,
                self.goal,
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

    def skip(self):
        if self.transition:
            self.transition.on_move_end = None
            self.transition.skip()
            self.scene.clock.unschedule(self.update)

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

    def skip(self):
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
        self.scene = scene
        scene.clock.schedule(self.done, self.delay)

    def skip(self):
        self.scene.clock.unschedule(self.done)
