import pygame
import os.path


# This is the directory in which graphics will be stored
IMAGE_DIR = 'graphics/'


def load_image(name):
    path = os.path.join(IMAGE_DIR, name + '.png')
    surf = pygame.image.load(path)
    return surf.convert_alpha()


def load_frames(base, num):
    for i in range(1, num + 1):
        yield load_image('%s-%d' % (base, i))
