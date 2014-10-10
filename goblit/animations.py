from collections import namedtuple
from pygame.transform import flip

from . import clock

DEFAULT_FRAME_RATE = 15


# A sprite and the (x, y) position at which it should be drawn, relative
# to the animation instance
Frame = namedtuple('Frame', 'sprite offset')

# Sentinel value to indicate looping until told to stop, rather than
# switching to a different animation
loop = object()

# A list of of frames plus the name of the next sequence to play when the
# animation ends.
#
# Set next_sequence to ``loop`` to make the animation loop forever.
Sequence = namedtuple('Sequence', 'frames next_sequence')


class Animation:
    def __init__(self, sequences, frame_rate=DEFAULT_FRAME_RATE):
        self.sequences = sequences
        self.frame_rate = frame_rate

    def create_instance(self, pos=(0, 0)):
        return AnimationInstance(self, pos)


class AnimationInstance:
    def __init__(self, animation, pos=(0, 0)):
        self.animation = animation
        self.pos = pos
        self.dir = dir
        self.play('default')  # Start default sequence
        clock.schedule_interval(self.next_frame, 1 / self.animation.frame_rate)

    def play(self, sequence_name):
        """Start playing the given sequence at the beginning."""
        self.playing = sequence_name
        self.currentframe = 0
        self.sequence = self.animation.sequences[sequence_name]

    def next_frame(self):
        """Called by the clock to increment the frame number."""
        self.currentframe += 1
        if self.currentframe >= len(self.sequence.frames):
            next = self.sequence.next_sequence
            if next is loop:
                self.currentframe = 0
            else:
                self.play(next)

    def draw(self, screen):
        """Draw the animation at coordinates given by self.pos.

        The current frame will be drawn at its corresponding offset.

        """
        frame = self.sequence.frames[self.currentframe]
        ox, oy = frame.offset
        x, y = self.pos
        sprite = frame.sprite
        if self.dir == 'right':
            sprite = flip(sprite, True, False)
        screen.blit(sprite, (x + ox, y + oy))
