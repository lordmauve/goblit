import pygame

from . import scene

screen = None


def init():
    global screen
    pygame.init()
    pygame.display.set_icon(pygame.image.load(scene.ICON))
    screen = pygame.display.set_mode((960, 620))
    pygame.display.set_caption(scene.TITLE)

    scene.load()


def dispatch(name, event):
    handler = getattr(scene, name, None)
    if handler:
        handler(**event.__dict__)


def run():
    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                dispatch('on_mouse_down', event)
            elif event.type == pygame.MOUSEMOTION:
                dispatch('on_mouse_move', event)
            elif event.type == pygame.KEYDOWN:
                dispatch('on_key_down', event)

        scene.update(dt / 1000.0)
        scene.draw(screen)
        pygame.display.flip()
