from backend import Backend
from contextlib import ExitStack

class System():
    def __init__(self):
        backend_ips = ['192.168.1.101']
        backend_lab = ['Data']
        self.backend = [Backend(*a) for a in zip(backend_lab, backend_ips)]

    def __enter__(self):
        with ExitStack() as stack:
            [stack.enter_context(b) for b in self.backend]
            self._stack = stack.pop_all()
        return self

    def __exit__(self, *context):
        self._stack.__exit__(self, *context)
