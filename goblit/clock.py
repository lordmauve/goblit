import heapq


__all__ = [
    'Clock', 'schedule', 'schedule_interval', 'unschedule'
]


class Clock:
    def __init__(self):
        self.t = 0
        self.events = []

    def schedule(self, callback, delay):
        heapq.heappush(self.events, (self.t + delay, callback, None))

    def schedule_interval(self, callback, delay):
        heapq.heappush(self.events, (self.t + delay, callback, delay))

    def unschedule(self, callback):
        self.events.remove(callback)

    def tick(self, dt):
        self.t += dt
        while self.events and self.events[0][0] < self.t:
            t, cb, repeat = heapq.heappop(self.events)
            try:
                cb()
            except Exception:
                import traceback
                traceback.print_exc()
            else:
                if repeat is not None:
                    self.schedule_inverval(cb, repeat)


clock = Clock()
tick = clock.tick
schedule = clock.schedule
schedule_interval = clock.schedule_interval
unschedule = clock.unschedule
