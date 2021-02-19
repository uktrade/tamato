class StdOutStdErrContext:
    """Wrapper for stdout or stderr, non closable streams to enable using them in a with statement."""

    def __init__(self, f):
        self.f = f

    def __enter__(self):
        return self.f

    def __exit__(self):
        pass
