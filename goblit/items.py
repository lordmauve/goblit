from .inventory import Item

# Why am I doing this? We should be able to build them dynamically?
Item('SOCK')
Item('KETTLE')
Item('PARROT')
Item('TEA SOCK', 'sock')
Item('MUG')
Item('MUG OF HOT WATER')
Item('MUG WITH TEA SOCK')
Item('CUP OF TEA')


def spawn_all(scene):
    h = 427
    scene.spawn_object_on_floor('SOCK', (291, 379))
    scene.spawn_object_on_floor('KETTLE', (892, h - 79))

    scene.spawn_object_near_navpoint('PARROT', (550, h - 232), 'NEAR PARROT')
    scene.spawn_object_near_navpoint('MUG', (432, h - 180), 'CABINET')
