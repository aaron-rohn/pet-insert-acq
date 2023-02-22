import socket, logging, threading, queue, time
import command as cmd
from gigex import Gigex, ignore_network_errors
from frontend import Frontend
from datetime import datetime
from logging.handlers import WatchedFileHandler

data_port = 5555

monitor_log = logging.getLogger("monitor")
fhandle = WatchedFileHandler("/mnt/acq/monitor.log")
monitor_log.addHandler(fhandle)
monitor_log.setLevel(logging.INFO)
monitor_log.propagate = False

class BackendAcq:
    def __init__(self, ip, stop):
        self.ip = ip
        self.stop = stop
        self.timeout = 0.1
        self.s = None

    def try_connect(self):
        if isinstance(self.s, socket.socket):
            self.s.close()

        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(self.timeout)
            self.s.connect((self.ip, data_port))
            logging.debug(f'{self.ip}: Acquisition connected')
        except Exception as e:
            self.s = None
            logging.debug(f'{self.ip}: Acquisition failed to connect, {e}')
            time.sleep(self.timeout)

    def __iter__(self):
        while not self.stop.is_set():
            try:
                yield self.s.recv(8192)
            except TimeoutError:
                yield b''
            except Exception as e:
                self.try_connect()
                yield b''

def acquire(ip, stop, sink, running = None):
    if running is None:
        running = threading.Event()

    if sink is None:
        return

    acq_inst = BackendAcq(ip, stop)
    running.set()

    monitor_log.info(f'{ip} {datetime.now()} acquisition: start')

    if isinstance(sink, str):
        logging.debug(f'Create new ACQ worker thread to {sink}')
        with open(sink, 'wb') as f:
            for d in acq_inst:
                f.write(d)

    elif isinstance(sink, socket.socket):
        logging.debug('Start online coincidence sorting')
        for d in acq_inst:
            sink.sendall(d)
        logging.debug('End online coincidence sorting')
        sink.close()

    else: # sink should be queue
        logging.debug(f'Create new ACQ worker thread to UI')
        for d in acq_inst:
            try:
                sink.put_nowait(d)
            except queue.Full: pass

    monitor_log.info(f'{ip} {datetime.now()} acquisition: stop')

class Backend():
    def __getattr__(self, attr):
        return lambda *args, **kwds: [getattr(f, attr)(*args, **kwds) for f in self.frontend]

    def __init__(self, ip):
        self.ip = ip
        self.gx = Gigex(ip)
        self.frontend = [Frontend(self, i) for i in range(4)]

        self.exit = threading.Event()
        self.dest = queue.Queue()

        self.ui_mon_queue = queue.Queue()
        self.ui_data_queue = queue.Queue(maxsize = 10)

    def __enter__(self):
        self.gx.start()
        self.acq_management_thread = threading.Thread(target = self.acq)
        self.monitor_thread = threading.Thread(target = self.mon)
        self.acq_management_thread.start()
        self.monitor_thread.start()
        return self

    def __exit__(self, *context):
        self.exit.set()
        self.dest.put(None)
        self.monitor_thread.join()
        self.acq_management_thread.join()
        self.gx.stop()

    def acq(self):
        acq_stop = threading.Event()
        acq_thread = threading.Thread(target = acquire,
                args = [self.ip, acq_stop, self.ui_data_queue])
        acq_thread.start()

        while True:
            vals = self.dest.get()

            acq_stop.set()
            acq_thread.join()
            acq_stop.clear()

            if vals is None: break

            acq_thread = threading.Thread(target = acquire,
                    args = [self.ip, acq_stop, *vals])
            acq_thread.start()

    def mon(self, interval = 10.0):
        while True:
            if self.get_status():
                temps = self.get_all_temps()
                currs = self.get_current()
                sgls  = self.get_counter(0, div = 3)
                self.ui_mon_queue.put((temps, currs, sgls))

                now = datetime.now()
                monitor_log.info(f'{self.ip} {now} current: {currs}')
                monitor_log.info(f'{self.ip} {now} temperature: {temps}')
                monitor_log.info(f'{self.ip} {now} singles: {sgls}')

            if self.exit.wait(interval):
                return

    @ignore_network_errors(False)
    def get_status(self):
        c = cmd.backend_status(10)
        return self.gx.send(c) == c

    @ignore_network_errors([True]*4)
    def get_power(self):
        resp = self.gx.send(cmd.set_power(False, [False]*4))
        return cmd.mask_to_bool(cmd.payload(resp))

    @ignore_network_errors([True]*4)
    def set_power(self, state = [False]*4):
        resp = self.gx.send(cmd.set_power(True, state))
        return cmd.mask_to_bool(cmd.payload(resp))

    @ignore_network_errors([-1]*4)
    def get_current(self):
        resp = [self.gx.send(cmd.get_current(m)) for m in range(4)]
        return [cmd.payload(m) for m in resp]

    @ignore_network_errors([-1]*4)
    def get_counter(self, ch, div = 0):
        resp = [self.gx.send(cmd.backend_counter(m,ch,div)) for m in range(4)]
        return [cmd.payload(r) << div for r in resp]

    @ignore_network_errors(None)
    def set_backend_otp_ocp(self, value = True):
        c = cmd.backend_reg_update(value,value)
        resp = self.gx.send(c)
        otp = bool((resp >> 13) & 0x1)
        ocp = bool((resp >> 12) & 0x1)
        return otp, ocp, resp & 0xFFF
