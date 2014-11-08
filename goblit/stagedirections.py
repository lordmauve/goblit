from .actions import (
    Pause, Spawn, MoveTo, Unspawn, SetPosition, Play, Face, FaceAway,
    FaceRight, SetBackground, Gain
)
from .binding import stagedirection


@stagedirection('pause')
def pause():
    return Pause(2)


@stagedirection('* enters')
def enter(character):
    return Spawn(character, 'DOOR') >> MoveTo(character, 'ENTRANCE')


@stagedirection('* is gone')
def is_gone(character):
    return Unspawn(character)


@stagedirection('* leaves')
def leaves(character):
    return MoveTo(character, 'DOOR') >> Unspawn(character)


@stagedirection('* moves to *')
def move(character, destination):
    return MoveTo(character, destination)


@stagedirection('* is standing by *')
@stagedirection('* is at *')
def set_position(character, location):
    return SetPosition(character, location)


@stagedirection('* is angry')
def angry(character):
    return Play(character, 'angry')


@stagedirection('* is disgusted')
def is_disgusted(character):
    return Play(character, 'disgusted')


@stagedirection('* turns back on *')
def turns_back_on(character, target):
    return FaceAway(character, target)


@stagedirection('* looks upstage')
def look_upstage(character):
    return Play(character, 'look-back')


@stagedirection('* looks out of window')
def look_out_of_window(character):
    return MoveTo(character, 'WINDOW') >> Play(character, 'look-back')


@stagedirection('* turns to face *')
def face_target(character, target):
    return Face(character, target)


@stagedirection('WIZARD TOX turns around')
def tox_turn_around():
    return Face('WIZARD TOX', 'GOBLIT') + Play('WIZARD TOX', 'sitting')


@stagedirection('WIZARD TOX turns back to desk')
def tox_turn_back_to_desk():
    return FaceRight('WIZARD TOX') + Play('WIZARD TOX', 'sitting-at-desk')


@stagedirection('WIZARD TOX stands up')
def tox_stand_up():
    return Play('WIZARD TOX', 'default') + SetBackground('room')


@stagedirection('* appears')
def appears(character):
    return (
        SetBackground('room-mephistopheles') +
        Spawn(character, 'CENTRE STAGE')
    )


@stagedirection('* begins summoning')
def begins_summoning(character):
    return Play(character, 'summoning')


@stagedirection('* blushes')
def blushes(character):
    return Play(character, 'blushing')


@stagedirection('* disappears')
def disappears(character):
    return (
        SetBackground('room-unlit') +
        Unspawn(character)
    )


@stagedirection('* gives *')
def gives(character, item):
    return (
        MoveTo(character, 'GOBLIT') >>
        Face('GOBLIT', character) >>
        Face(character, 'GOBLIT') >>
        Gain(item)
    )


@stagedirection('* is filled')
def is_filled(character):
    return Play(character, 'filled')


@stagedirection('* turns blue')
def turns_blue(character):
    raise NotImplementedError('turns_blue should return an action chain')


@stagedirection('* starts bubbling')
def starts_bubbling(character):
    raise NotImplementedError('starts_bubbling should return an action chain')


@stagedirection('* fires catapult')
def fires_catapult(character):
    raise NotImplementedError('fires_catapult should return an action chain')


@stagedirection('* has candles')
def has_candles(character):
    raise NotImplementedError('has_candles should return an action chain')


@stagedirection('* is lit')
def is_lit(character):
    raise NotImplementedError('is_lit should return an action chain')


@stagedirection('* has crystals')
def has_crystals(character):
    raise NotImplementedError('has_crystals should return an action chain')


@stagedirection('* is ready')
def is_ready(character):
    raise NotImplementedError('is_ready should return an action chain')

