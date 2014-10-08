class Action:
    """An action the player can take."""
    def __init__(self, name, callback):
        self.name = name
        self.callback = callback

    def __call__(self):
        try:
            self.callback()
        except Exception:
            import traceback
            traceback.print_exc()

