import socket
import threading
import command as cmd
from gigex import Gigex
from frontend import Frontend

def mask_to_bool(val, n = 4):
    return [bool(val & (1 << i)) for i in range(n)]

data_port = 5555

class BackendWriteFunc():
    def __init__(self):
        self.lock = threading.Lock()
        self.func = lambda data: None

    def __call__(self, data):
        with self.lock:
            self.func(data)

    def set(self, func):
        with self.lock:
            self.__setattr__('func', func)

class Backend():

    def acq(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        s.connect((self.ip,data_port))

        while not self.finished.is_set():
            try:
                d = s.recv(4096)
                self.wr_func(d)
            except socket.timeout as e:
                pass

        s.close()

    def mon(self, interval = 5.0):
        while not self.finished.wait(interval):
            if self.mon_cb is not None:
                self.mon_cb()

    def __enter__(self):
        self.acq_thread = threading.Thread(target = self.acq)
        self.mon_thread = threading.Thread(target = self.mon)
        self.finished.clear()
        self.acq_thread.start()
        self.mon_thread.start()
        return self

    def __exit__(self, *context):
        self.finished.set()
        self.acq_thread.join()
        self.mon_thread.join()

    def __init__(self, ip):
        self.ip = ip
        self.gx = Gigex(self.ip)
        self.finished = threading.Event()
        self.wr_func = BackendWriteFunc()
        self.acq_thread = None
        self.mon_thread = None
        self.mon_cb = None
        self.frontend = [Frontend(self, i) for i in range(4)]

    def __getattr__(self, attr):
        return lambda *args, **kwds: [getattr(f, attr)(*args, **kwds) for f in self.frontend]

    def exec(self, cmd_int):
        with self.gx:
            return self.gx.spi_query(cmd_int)

    def get_status(self):
        resp = self.exec(cmd.backend_status(10))
        value_out = cmd.payload(resp)
        return (value_out == 10)

    def get_rx_status(self):
        resp = self.exec(cmd.gpio_rd_rx_err())
        return mask_to_bool(cmd.payload(resp) & 0xF)

    def get_tx_status(self):
        resp = self.exec(cmd.gpio_rd_tx_idle())
        return mask_to_bool(cmd.payload(resp) & 0xF)

    def get_set_power(self, update = False, state = [False]*4):
        resp = self.exec(cmd.set_power(update, state))
        return mask_to_bool(cmd.payload(resp))

    def get_current(self):
        resp = [self.exec(cmd.get_current(m)) for m in range(4)]
        return [cmd.payload(m) for m in resp]

