def do_all(*callbacks):
    """Return a function that will call all the given functions."""
    def go():
        for c in callbacks:
            try:
                c()
            except Exception:
                import traceback
                traceback.print_exc()
    return go


class Action:
    """An action the player can take."""
    def __init__(self, name, callback=None):
        self.name = name
        self.callbacks = [callback] if callback else []

    def __call__(self):
        for c in self.callbacks:
            try:
                c()
            except Exception:
                import traceback
                traceback.print_exc()

    def chain(self, handler):
        """Call another handler after this one."""
        self.callbacks.append(handler)
