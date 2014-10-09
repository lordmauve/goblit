from .inventory import Item

sock = Item('sock')
kettle = Item('kettle')
parrot = Item('parrot')


def spawn_all(scene):
    h = 427
    scene.spawn_object_on_floor(sock, (291, 379))
    scene.spawn_object_on_floor(kettle, (892, h - 79))
    # FIXME: not on floor
    scene.spawn_object_on_floor(parrot, (550, h - 232))
