from .inventory import Item

Item('TEA SOCK', 'sock')


def spawn_all(scene):
    h = 427
    scene.spawn_object_on_floor('SOCK', (291, 379))
    scene.spawn_object_on_floor('KETTLE', (892, h - 79))

    scene.spawn_object_near_navpoint('PARROT', (550, h - 232), 'NEAR PARROT')
    scene.spawn_object_near_navpoint('MUG', (432, h - 180), 'CABINET')
    scene.spawn_object_near_navpoint('Y WAND', (242, h - 177), 'BOOKCASE BACK')
