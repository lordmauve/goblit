from .inventory import Item, SceneItem
from .animations import Sequence, Frame, Animation, loop

Item('TEA SOCK', 'sock')
Item('EX PARROT', 'parrot')


def spawn_all(scene):
    h = 427
    scene.spawn_object_on_floor('SOCK', (291, 379))

    scene.spawn_fixed_object_near_navpoint('CHANDELIER', (423, h - 407), 'CENTRE STAGE')

    scene.spawn_object_near_navpoint('KETTLE', (892, h - 79), 'FIREPLACE')
    scene.spawn_object_near_navpoint('PARROT', (550, h - 232), 'NEAR PARROT')
    scene.spawn_object_near_navpoint('MUG', (432, h - 180), 'CABINET')
    scene.spawn_object_near_navpoint('Y WAND', (242, h - 177), 'BOOKCASE BACK')
    scene.spawn_object_near_navpoint('CANDLESTICK', (816, h - 238), 'BESIDE DESK')
    scene.spawn_object_near_navpoint('LETTER OPENER', (781, h - 122), 'BESIDE DESK')
