import os, shutil, logging, time, threading, glob
from contextlib import ExitStack
from sync import Sync
from backend import Backend

class System():
    def __init__(self):
        self.sync = Sync('192.168.1.100')
        backend_ips = ['192.168.1.101', '192.168.1.102', '192.168.2.103', '192.168.2.104']
        self.data_dir = '/opt/acq'
        self.backend = [Backend(a) for a in backend_ips]

    def __getattr__(self, attr):
        return lambda *args, **kwds: [getattr(b, attr)(*args, **kwds) for b in self.backend]

    def __enter__(self):
        self.sync.set_network_led(clear = False)
        #self.set_network_led(clear = False)
        with ExitStack() as stack:
            [stack.enter_context(b) for b in self.backend]
            self._stack = stack.pop_all()
        return self
    
    def __exit__(self, *context):
        self.sync.set_network_led(clear = True)
        #self.set_network_led(clear = True)
        self._stack.__exit__(self, *context)

    def set_power(self, states = [[False]*4]*4):
        return [b.set_power(s) for b,s in zip(self.backend, states)]

    def sys_status(self, data_queue):
        sync     = self.sync.get_status()
        backend  = self.get_status()
        power    = self.get_power()
        enum     = self.get_physical_idx()
        data_queue.put((sync, backend, power, enum))

    def acq_start(self, finished):
        for be in self.backend:
            with be.count_rate_queue.mutex:
                be.count_rate_queue.queue.clear()

        self.detector_disable(True)
        time.sleep(1)

        running = []

        for be in self.backend:
            fname = os.path.join(self.data_dir, be.ip + '.SGL')
            r = threading.Event()
            be.put((fname, r))
            running.append(r)

        [r.wait() for r in running]
        self.sync.sync_reset()
        self.detector_disable(False)
        finished.set()

    def acq_stop(self, finished, data_dir):
        self.detector_disable(True)

        for be in self.backend:
            be.put((be.ui_data_queue,))

        if data_dir:
            sgl_files = glob.glob('*.SGL', root_dir = self.data_dir)
            sgl_files = [os.path.join(self.data_dir, f) for f in sgl_files]

            try:
                for f in sgl_files:
                    shutil.move(f, data_dir)
            except PermissionError as e:
                logging.warning('Failed to move acquition files',
                        exc_info = e)

        finished.set()

