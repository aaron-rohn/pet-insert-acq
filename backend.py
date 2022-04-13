import socket, logging, threading, queue
import command as cmd
from gigex import Gigex, ignore_network_errors
from frontend import Frontend

data_port = 5555

class BackendAcq:
    def __init__(self, ip, stop):
        self.ip = ip
        self.stop = stop

    def __enter__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(1)

        try:
            self.s.connect((self.ip, data_port))
            logging.debug(f'{self.ip}: Acquisition connected')
        except (OSError, TimeoutError, ConnectionError):
            logging.warning(f'{self.ip}: Acquisition failed')
            self.s = None

        return self

    def __exit__(self, *context):
        if self.s is not None:
            logging.debug(f'{self.ip}: Stop acquisition')
            self.s.close()

    def __iter__(self):
        if self.s is None:
            return
        
        logging.debug(f'{self.ip}: Acquisition started')

        while not self.stop.is_set():
            try:
                yield self.s.recv(4096)
            except TimeoutError:
                yield b''
            except Exception as e:
                logging.warning(f'{self.ip}: Failed to receive data, {repr(e)}')
                yield b''

def acquire(ip, stop, sink, running = None):
    if running is None:
        running = threading.Event()

    with BackendAcq(ip, stop) as acq_inst:
        if isinstance(sink, str):
            logging.debug(f'Create new ACQ worker thread to {sink}')
            with open(sink, 'wb') as f:
                running.set()
                for d in acq_inst:
                    f.write(d)

        else:
            logging.debug(f'Create new ACQ worker thread to UI')
            running.set()
            for d in acq_inst:
                try:
                    sink.put_nowait(d)
                except queue.Full: pass

class Backend():
    def __getattr__(self, attr):
        return lambda *args, **kwds: [getattr(f, attr)(*args, **kwds) for f in self.frontend]

    def __init__(self, ip):
        self.ip = ip
        self.gx = Gigex(ip)
        self.frontend = [Frontend(self, i) for i in range(4)]

        self.exit = threading.Event()
        self.dest = queue.Queue()
        self.cv = threading.Condition()

        self.count_rate_queue = queue.Queue()
        self.ui_mon_queue = queue.Queue()
        self.ui_data_queue = queue.Queue(maxsize = 10)

    def __enter__(self):
        self.acq_management_thread = threading.Thread(
                target = self.acq, daemon = False)
        self.monitor_thread = threading.Thread(
                target = self.mon, daemon = True)

        self.exit.clear()
        self.acq_management_thread.start()
        self.monitor_thread.start()
        return self

    def __exit__(self, *context):
        self.exit.set()

        with self.cv:
            self.cv.notify_all()

        self.monitor_thread.join()
        self.acq_management_thread.join()

    def acq(self):
        acq_stop = threading.Event()
        acq_thread = threading.Thread(target = acquire,
                args = [self.ip, acq_stop, self.ui_data_queue])
        acq_thread.start()

        with self.cv:
            while True:
                self.cv.wait_for(lambda: (self.exit.is_set() or
                                          not self.dest.empty()))

                acq_stop.set()
                acq_thread.join()
                acq_stop.clear()

                if self.exit.is_set(): break
                vals = self.dest.get()

                acq_thread = threading.Thread(target = acquire,
                        args = [self.ip, acq_stop, *vals])

                acq_thread.start()

        logging.debug("Exit acq management thread")

    def mon(self, interval = 10.0):
        while True:
            temps = self.get_all_temps()
            currs = self.get_current()
            logging.info(f'{self.ip}: {currs}')
            self.ui_mon_queue.put_nowait((temps, currs))
            self.count_rate_queue.put(self.get_counter(0))

            if self.exit.wait(interval):
                break

        logging.debug("Exit monitor thread")

    def put(self, val):
        self.dest.put(val)
        with self.cv:
            self.cv.notify_all()

    @ignore_network_errors(None)
    def backend_reset_soft(self):
        r1 = self.gx.send(cmd.rst_soft(clear = False))
        r2 = self.gx.send(cmd.rst_soft(clear = True))
        return (cmd.payload(r1) == 1) & (cmd.payload(r2) == 0)

    @ignore_network_errors(None)
    def backend_reset_hard(self):
        with self.gx:
            self.gx.spi(cmd.rst_hard())

    @ignore_network_errors(None)
    def set_network_led(self, clear = False):
        self.gx.send(cmd.backend_network_set(clear))

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
    def get_counter(self, ch):
        resp = [self.gx.send(cmd.backend_counter(m,ch)) for m in range(4)]
        return [cmd.payload(r) for r in resp]
