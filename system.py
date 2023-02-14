import os, shutil, logging, time, threading, glob, socket, subprocess, sys
from contextlib import ExitStack
from sync import Sync
from backend import Backend

class System():
    def __init__(self):
        self.sync = Sync('192.168.1.100')
        backend_ips = ['192.168.1.101', '192.168.1.102', '192.168.1.103', '192.168.1.104']
        self.data_dir = '/mnt/acq'
        self.backend = [Backend(a) for a in backend_ips]

    def __getattr__(self, attr):
        return lambda *args, **kwds: [getattr(b, attr)(*args, **kwds) for b in self.backend]

    def __enter__(self):
        with ExitStack() as stack:
            [stack.enter_context(b) for b in ([self.sync] + self.backend)]
            self._stack = stack.pop_all()
        return self
    
    def __exit__(self, *context):
        self._stack.__exit__(self, *context)

    def set_power(self, states = [[False]*4]*4):
        return [b.set_power(s) for b,s in zip(self.backend, states)]

    def sys_status(self, data_queue):
        sync     = self.sync.get_status()
        backend  = self.get_status()
        power    = self.get_power()
        enum     = self.get_physical_idx()
        data_queue.put((sync, backend, power, enum))

    def acq_start(self, finished, coincidences = False):
        self.sorter = None
        if coincidences:
            logging.debug('Start online coincidence processor')
            self.sorter = subprocess.Popen(['/usr/local/bin/sorter', '/mnt/acq/online.COIN'],
                                           stdout = sys.stdout, stderr = sys.stderr)

        self.detector_disable(True)
        time.sleep(1)

        running = []
        for idx, be in enumerate(self.backend):
            if coincidences:
                try:
                    sink = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
                    sink.connect(('127.0.0.1', 10000 + idx))
                    logging.debug(f'Connected to online coincidence processor on port {10000 + idx}')
                except:
                    # online coincidence sorting isn't running
                    logging.exception('Failed to connect to online coincidence processor')
                    sink = be.ui_data_queue
            else:
                sink = os.path.join(self.data_dir, be.ip + '.SGL')

            r = threading.Event()
            be.dest.put((sink, r))
            running.append(r)

        [r.wait() for r in running]
        time.sleep(1)
        self.sync.sync_reset()
        self.detector_disable(False)
        finished.set()

    def acq_stop(self, finished, data_dir):
        self.detector_disable(True)

        for be in self.backend:
            be.dest.put((be.ui_data_queue,))

        # Coincidence sorter process should exit when sockets close, if it was running
        if self.sorter is not None:
            try:
                self.sorter.wait(10.0)
            except subprocess.TimeoutExpired:
                logging.exception('Online coincidence sorter did not stop cleanly, killing')
                self.sorter.kill()
            self.sorter = None

            try:
                shutil.move('/mnt/acq/online.COIN', os.path.join(data_dir, 'online.COIN'))
            except:
                logging.exception('Error moving online coincidence sorted file')

        # Move the singles files to the selected directory
        elif data_dir:
            sgl_files = glob.glob('*.SGL', root_dir = self.data_dir)
            sgl_files = [os.path.join(self.data_dir, f) for f in sgl_files]
            try:
                for f in sgl_files: shutil.move(f, data_dir)
            except:
                logging.exception('Failed to move acquition files')

        finished.set()

