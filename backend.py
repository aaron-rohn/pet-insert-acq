import time
import socket
import threading
import queue

import command as cmd
from gigex import Gigex
from frontend import Frontend

class Backend():
    data_port = 5555

    @staticmethod
    def mask_to_bool(val, n = 4):
        return [bool(val & (1 << i)) for i in range(n)]

    @staticmethod
    def acq(ip, output, finished):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        s.connect((ip,Backend.data_port))

        while not finished.is_set():
            try:
                d = s.recv(4096)
                output(d)
            except socket.timeout as e:
                pass

    def __enter__(self):
        args = (self.ip, self.data_output, self.finished)
        self.acq_thread = threading.Thread(target = Backend.acq, args = args)
        self.finished.clear()
        self.acq_thread.start()
        return self

    def __exit__(self, *context):
        self.finished.set()
        self.acq_thread.join()

    def __init__(self, ip):
        self.ip = ip
        self.gx = Gigex(self.ip)

        with self.gx:
            pass
            #self.gx.reboot()

        self.finished = threading.Event()
        self.acq_thread = None
        self.data_output = lambda data: None
        self.frontend = [Frontend(self, i) for i in range(4)]

    def __getattr__(self, attr):
        return lambda: [getattr(f, attr)() for f in self.frontend]

    def exec(self, cmd_int):
        with self.gx:
            return self.gx.spi_query(cmd_int)

    def get_status(self):
        resp = self.exec(cmd.backend_status(10))
        value_out = cmd.payload(resp)
        return (value_out == 10)

    def get_rx_status(self):
        resp = self.exec(cmd.gpio_rd_rx_err())
        return Backend.mask_to_bool(cmd.payload(resp) & 0xF)

    def get_tx_status(self):
        resp = self.exec(cmd.gpio_rd_tx_idle())
        return Backend.mask_to_bool(cmd.payload(resp) & 0xF)

    def get_set_power(self, update = False, state = [False]*4):
        resp = self.exec(cmd.set_power(update, state))
        return Backend.mask_to_bool(cmd.payload(resp))

    def get_current(self):
        resp = [self.exec(cmd.get_current(m)) for m in range(4)]
        return [cmd.payload(m) for m in resp]

