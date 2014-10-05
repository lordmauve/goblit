import pygame
from pygame.font import Font
from .animations import Sequence, Frame, Animation, loop
from .loaders import load_image


GOBLIT = Animation({
    'default': Sequence([
        Frame(load_image('goblit-standing'), (-18, -81))
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


class Goblit(object):
    COLOR = (255, 255, 255)

    def __init__(self):
        self.sprite = GOBLIT.create_instance((100, 400))
        self.sprite.dir = 'right'
        self.words = None

    def say(self, line):
        x, y = self.sprite.pos
        self.words = FontBubble(line, (x, y - 120), self.COLOR)

    def draw(self, screen):
        self.sprite.draw(screen)
        if self.words:
            self.words.draw(screen)
