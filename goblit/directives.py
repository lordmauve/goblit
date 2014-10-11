import re
import random
from .errors import ScriptError
from .scene import player, scene, directive
from .dialogue import DialogueChoice, AllDialogueChoice
from .inventory import inventory


@directive
def directive_destroy(directive):
    """Destroy an object."""
    name = directive.data
    obj = scene.get(name)
    if obj:
        scene.unspawn_object(obj)


def directive_allow(directive):
    scene.object_scripts[directive.data] = directive
    player.do_next()

directive_deny = directive_allow


@directive
def directive_unbind(directive):
    scene.object_scripts[directive.data] = None


@directive
def directive_rename(directive):
    mo = re.match(r'^([A-Z ]+?)\s*->\s*([A-Z ]+)$', directive.data)
    if not mo:
        raise ScriptError("Couldn't parse rename directive %r" % directive.data)
    try:
        scene.rename(*mo.groups())
    except KeyError as e:
        raise ScriptError("No such object %r" % e.args[0])


@directive
def directive_gain(directive):
    """Gain an item."""
    try:
        inventory.gain(directive.data)
    except KeyError:
        raise ScriptError("No such item %s" % directive.data)


@directive
def directive_craft(directive):
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

@directive
def directive_lose(directive):
    """Lose an item."""
    try:
        inventory.lose(directive.data)
    except KeyError:
        raise ScriptError("No such item %s" % directive.data)
    except ValueError:
        raise ScriptError("Player does not have %s" % directive.data)


def directive_choice(directive):
    """On its own, does nothing. Just plays the contents.

    Useful for grouping.

    """
    player.play_subscript(directive)


def directive_random(directive):
    """Pick one contents line at random.

    For example,

    .. random::

        GOBLIT: Maybe I'll say this.
        GOBLIT: Maybe I'll say that.
        .. choice::
            GOBLIT: Maybe I'll say this...
            GOBLIT: ...then that.

    """
    from .scripts import Script
    s = Script([random.choice(directive.contents)])
    player.skippable = True
    player.play_subscript(s)


def directive_choose_any(directive):
    """A dialogue in which the player can choose any one option."""
    player.dialogue_choice = DialogueChoice(player, directive)


def directive_choose_all(directive):
    """A dialogue in which the player will go through all options."""
    player.dialogue_choice = AllDialogueChoice(player, directive)
