from .loaders import load_image

room_bg = None
objects = []
goblit = None


def load():
    global room_bg, goblit
    room_bg = load_image('room')
    from .actors import Goblit
    goblit = Goblit()
    objects.append(goblit)
    goblit.say("Blimey, it's cold in here")


def update(dt):
    pass


def draw(screen):
    screen.blit(room_bg, (0, 0))

    for o in objects:
        o.draw(screen)
