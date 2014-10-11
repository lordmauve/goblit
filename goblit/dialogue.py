from functools import partial
from . import scripts
from .errors import ScriptError
from .actions import Action
from .actors import FontBubble


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
