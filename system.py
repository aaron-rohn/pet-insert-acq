from sync import Sync
from backend import Backend

class System():
    def __init__(self):
        self.sync = Sync('192.168.1.100')
        backend_ips = ['192.168.1.101', '192.168.1.102', '192.168.2.103', '192.168.2.104']
        #backend_ips = ['127.0.1.1']
        self.backend = [Backend(a) for a in backend_ips]

    def __getattr__(self, attr):
        return lambda *args, **kwds: [getattr(b, attr)(*args, **kwds) for b in self.backend]

    def set_power(self, states = [[False]*4]*4):
        return [b.set_power(s) for b,s in zip(self.backend, states)]
