import pygame

from . import scene

screen = None


def init():
    global screen
    pygame.init()
    screen = pygame.display.set_mode((960, 600))
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

        scene.update(dt)
        scene.draw(screen)
        pygame.display.flip()
