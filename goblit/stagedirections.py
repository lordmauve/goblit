from .actions import (
    Pause, Spawn, MoveTo, Unspawn, SetPosition, Play, Face, FaceAway,
    FaceRight, SetBackground, Gain
)
from .binding import stagedirection


@stagedirection('pause')
def pause(scene):
    return Pause(2)


@stagedirection('* enters')
def enter(scene, character):
    return Spawn(character, 'DOOR') >> MoveTo(character, 'ENTRANCE')


@stagedirection('* is gone')
def is_gone(scene, character):
    return Unspawn(character)


@stagedirection('* leaves')
def leaves(scene, character):
    return MoveTo(character, 'DOOR') >> Unspawn(character)


@stagedirection('* moves to *')
def move(scene, character, destination):
    return MoveTo(character, destination)


@stagedirection('* is standing by *')
@stagedirection('* is at *')
def set_position(scene, character, location):
    return SetPosition(character, location)


@stagedirection('* is angry')
def angry(scene, character):
    return Play(character, 'angry')


@stagedirection('* is disgusted')
def is_disgusted(scene, character):
    return Play(character, 'disgusted')


@stagedirection('* turns back on *')
def turns_back_on(scene, character, target):
    return FaceAway(character, target)


@stagedirection('* looks upstage')
def look_upstage(scene, character):
    return Play(character, 'look-back')


@stagedirection('* looks out of window')
def look_out_of_window(scene, character):
    return MoveTo(character, 'WINDOW') >> Play(character, 'look-back')


@stagedirection('* turns to face *')
def face_target(scene, character, target):
    return Face(character, target)


@stagedirection('WIZARD TOX turns around')
def tox_turn_around(scene):
    return Face('WIZARD TOX', 'GOBLIT') + Play('WIZARD TOX', 'sitting')


@stagedirection('WIZARD TOX turns back to desk')
def tox_turn_back_to_desk(scene):
    return FaceRight('WIZARD TOX') + Play('WIZARD TOX', 'sitting-at-desk')


@stagedirection('WIZARD TOX stands up')
def tox_stand_up(scene):
    return Play('WIZARD TOX', 'default') + SetBackground('room')


@stagedirection('* appears')
def appears(scene, character):
    return (
        SetBackground('room-mephistopheles') +
        Spawn(character, 'CENTRE STAGE')
    )


@stagedirection('* begins summoning')
def begins_summoning(scene, character):
    return Play(character, 'summoning')


@stagedirection('* blushes')
def blushes(scene, character):
    return Play(character, 'blushing')


@stagedirection('* disappears')
def disappears(scene, character):
    return (
        SetBackground('room-unlit') +
        Unspawn(character)
    )


@stagedirection('* gives *')
def gives(scene, character, item):
    return (
        MoveTo(character, 'GOBLIT') >>
        Face('GOBLIT', character) >>
        Face(character, 'GOBLIT') >>
        Gain(item)
    )


@stagedirection('* is filled')
def is_filled(scene, character):
    return Play(character, 'filled')


@stagedirection('CAULDRON turns blue')
def turns_blue(scene):
    scene.get_actor('CAULDRON').turn_blue()


@stagedirection('CAULDRON starts bubbling')
def starts_bubbling(scene):
    scene.get_actor('CAULDRON').start_bubbling()


@stagedirection('* fires catapult')
def fires_catapult(scene, character):
    raise NotImplementedError('fires_catapult should return an action chain')


@stagedirection('PENTAGRAM has candles')
def has_candles(scene):
    scene.get_actor('PENTAGRAM').add_candles()


@stagedirection('PENTAGRAM is lit')
def is_lit(scene):
    scene.get_actor('PENTAGRAM').light_candles()


@stagedirection('PENTAGRAM has crystals')
def has_crystals(scene):
    scene.get_actor('PENTAGRAM').add_crystals()


@stagedirection('* is ready')
def is_ready(scene, character):
    scene.get_actor(character).make_ready()

