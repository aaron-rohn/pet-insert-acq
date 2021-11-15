from sync import Sync
from backend import Backend
from contextlib import ExitStack

class System():
    def __init__(self):
        self.sync = Sync('192.168.1.100')
        backend_ips = ['192.168.1.101', '192.168.1.102', '192.168.2.103', '192.168.2.104']
        #backend_ips = ['192.168.2.104']
        self.backend = [Backend(a) for a in backend_ips]
        self._stack = None

    def __enter__(self):
        self.sync.set_network_led(clear = False)
        with ExitStack() as stack:
            [stack.enter_context(b) for b in self.backend]
            self._stack = stack.pop_all()
        return self
    
    def __exit__(self, *context):
        self.sync.set_network_led(clear = True)
        if self._stack is not None:
            self._stack.__exit__(self, *context)

    def __getattr__(self, attr):
        return lambda *args, **kwds: [getattr(b, attr)(*args, **kwds) for b in self.backend]

    def set_power(self, states = [[False]*4]*4):
        return [b.set_power(s) for b,s in zip(self.backend, states)]
