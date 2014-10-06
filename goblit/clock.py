import heapq
from weakref import ref
from types import MethodType

__all__ = [
    'Clock', 'schedule', 'schedule_interval', 'unschedule'
]


def weak_method(method):
    """Quick weak method ref in case users aren't using Python 3.4"""
    selfref = ref(method.__self__)
    funcref = ref(method.__func__)

    def weakref():
        self = selfref()
        func = funcref()
        if self is None or func is None:
            return None
        return func.__get__(self)
    return weakref


class Event:
    def __init__(self, time, cb, repeat=None):
        self.time = time
        self.repeat = repeat
        if isinstance(cb, MethodType):
            self.cb = weak_method(cb)
        else:
            self.cb = ref(cb)
        self.name = str(cb)
        self.repeat = repeat

    def __lt__(self, ano):
        return self.time < ano.time

    def __gt__(self, ano):
        return self.time > ano.time

    def __le__(self, ano):
        return self.time <= ano.time

    def __ge__(self, ano):
        return self.time >= ano.time

    def __eq__(self, ano):
        return self.time == ano.time

    @property
    def callback(self):
        cb = self.cb()
        if cb is None:
            print("%s has expired" % self.name)
        return cb


class Clock:
    def __init__(self):
        self.t = 0
        self.events = []

    def schedule(self, callback, delay):
        heapq.heappush(self.events, Event(self.t + delay, callback, None))

    def schedule_interval(self, callback, delay):
        heapq.heappush(self.events, Event(self.t + delay, callback, delay))

    def unschedule(self, callback):
        self.events = [e for e in self.events if e.callback is callback]
        heapq.heapify(self.events)

    def tick(self, dt):
        self.t += dt
        while self.events and self.events[0].time <= self.t:
            ev = heapq.heappop(self.events)
            cb = ev.callback
            if not cb:
                continue
            try:
                cb()
            except Exception:
                import traceback
                traceback.print_exc()
            else:
                if ev.repeat is not None:
                    self.schedule_interval(cb, ev.repeat)


clock = Clock()
tick = clock.tick
schedule = clock.schedule
schedule_interval = clock.schedule_interval
unschedule = clock.unschedule
