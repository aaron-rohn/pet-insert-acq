import os
import socket
import threading
import queue
import types
import command as cmd
from gigex import Gigex
from frontend import Frontend

data_port = 5555

class Backend():

    def acq(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        s.connect((self.ip,data_port))

        f = open(os.devnull, "wb")
        ui = None

        while not self.finished.is_set():
            try:
                d = s.recv(4096)
            except socket.timeout as e:
                d = b''

            f.write(d)

            if ui is not None:
                try:
                    ui.insert('end', str(d) + "\n")
                    ui.yview('end')
                except RuntimeError as e:
                    # happens when main thread has already exited
                    break

            if self.update_queue.is_set():
                self.update_queue.clear()

                if not self.file_queue.empty():
                    f.close()
                    try:
                        f = open(self.file_queue.get(), 'wb')
                    except Exception as e:
                        print("Error opening data output file: {}".format(str(e)))
                        f = open(os.devnull, 'wb')

                if not self.ui_queue.empty():
                    ui = self.ui_queue.get()

        f.close()
        s.close()

    def mon(self, interval = 5.0):
        while not self.finished.wait(interval):
            if self.mon_cb is not None:
                try:
                    self.mon_cb()
                except RuntimeError as e:
                    # UI thread has exited
                    break

    def __init__(self, ip):
        self.ip = ip
        self.gx = Gigex(self.ip)
        self.acq_thread = None
        self.mon_thread = None
        self.finished = threading.Event()
        self.update_queue = threading.Event()
        self.file_queue = queue.Queue()
        self.ui_queue = queue.Queue()
        self.mon_cb = None
        self.frontend = [Frontend(self, i) for i in range(4)]

    def __enter__(self):
        print("enter")
        self.acq_thread = threading.Thread(target = self.acq, daemon = True)
        self.mon_thread = threading.Thread(target = self.mon, daemon = True)
        self.finished.clear()
        self.acq_thread.start()
        #self.mon_thread.start()
        self.set_network_led(clear = False)
        return self

    def __exit__(self, *context):
        print("exit")
        self.set_network_led(clear = True)
        self.finished.set()
        self.acq_thread.join()
        #self.mon_thread.join()

    def __getattr__(self, attr):
        return lambda *args, **kwds: [getattr(f, attr)(*args, **kwds) for f in self.frontend]

    def exec(self, cmd_int):
        with self.gx:
            return self.gx.spi_query(cmd_int)

    def reset(self):
        with self.gx:
            self.gx.spi(cmd.rst())

    def flush(self):
        with self.gx:
            self.gx.flush()

    def set_network_led(self, clear = False):
        self.exec(cmd.backend_network_set(clear))

    def get_status(self):
        c = cmd.backend_status(10)
        return self.exec(c) == c

    def get_rx_status(self):
        resp = self.exec(cmd.gpio_rd_rx_err())
        if resp is None:
            return [True]*4 # True indicates error
        else:
            return cmd.mask_to_bool(cmd.payload(resp) & 0xF)

    def get_power(self):
        resp = self.exec(cmd.set_power(False, [False]*4))
        return None if resp is None else cmd.mask_to_bool(cmd.payload(resp))

    def set_power(self, state = [False]*4):
        resp = self.exec(cmd.set_power(True, state))
        return None if resp is None else cmd.mask_to_bool(cmd.payload(resp))

    def get_current(self):
        resp = [self.exec(cmd.get_current(m)) for m in range(4)]
        return [-1 if resp is None else cmd.payload(m) for m in resp]

