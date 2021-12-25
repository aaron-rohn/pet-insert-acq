import os, socket, time, queue, threading
import tkinter as tk
from tkinter import filedialog
from frontend_ui import FrontendUI

class Acq:
    def __init__(self, ip, port, stop):
        self.ip = ip
        self.port = port
        self.stop = stop

    def __enter__(self):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(0.1)
            self.s.connect((self.ip,self.port))
        except (TimeoutError, ConnectionError):
            # socket should connect to gigex on first try
            # system might not be turned on
            print("Acquisiton failed to connect to target")
            self.s = None

        return self

    def __exit__(self, *context):
        self.s.close()

    def __iter__(self):
        if self.s is None:
            return

        while not self.stop.is_set():
            try:
                yield self.s.recv(4096)
            except (TimeoutError, ConnectionError):
                yield b''

def acq_ui(ip, port, stop, display):
    # acquire data and send it to the UI
    with Acq(ip, port, stop) as acq_inst:
        for d in acq_inst:
            try:
                display.delete(1.0, 'end')
                display.insert('end', str(d) + "\n")
            except RuntimeError:
                pass

def acq_file(ip, port, stop, fname):
    # acquire data and save it to a file
    with Acq(ip, port, stop) as acq_inst:
        with open(fname, 'wb') as f:
            for d in acq_inst:
                f.write(d)

class BackendUI():

    def acq(self):
        acq_stop = threading.Event()
        args = [self.backend.ip, self.backend.data_port, acq_stop]

        # spawn an acq thread to start
        acq_thread = threading.Thread(target = acq_ui, args = args + [self.data], daemon = True)
        acq_thread.start()

        # monitor the UI thread and spawn acq_ui and acq_file as necessary
        self.cv.acquire()
        while self.cv.wait():
            if self.exit.is_set():
                self.cv.release()
                break

            # should be None to display to UI, or a file name
            fname = self.dest.get_nowait()

            # join the old acq thread
            acq_stop.set()
            acq_thread.join()
            acq_stop.clear()

            # determine if the new thread directs to UI or a file
            if fname is None:
                acq_target = acq_ui
                a = args + [self.data]
            else:
                acq_target = acq_file
                a = args + [fname]

            # start the new thread
            acq_thread = threading.Thread(target = acq_target, args = a, daemon = True)
            acq_thread.start()

        # join the acq thread when finishing
        acq_stop.set()
        acq_thread.join()

    def __getattr__(self, attr):
        return getattr(self.backend, attr)

    def __enter__(self):
        self.exit = threading.Event()
        self.cv = threading.Condition()
        self.dest = queue.Queue()

        self.acq_management_thread = threading.Thread(target = self.acq, daemon = True)
        self.acq_management_thread.start()
        return self

    def __exit__(self, *context):
        self.exit.set()
        with self.cv:
            self.cv.notify()

        self.acq_management_thread.join()

    def acq_start(self, destination):
        self.dest.put(destination)
        with self.cv:
            self.cv.notify()

    def acq_end(self):
        self.dest.put(None)
        self.cv.acquire()
        self.cv.notify()
        self.cv.release()

    def __init__(self, backend_instance, status_frame, acq_frame):
        self.backend = backend_instance
        self.status_frame = tk.Frame(status_frame)

        # Frame with Label, status, and data output text field
        self.common = tk.Frame(self.status_frame)
        self.status_label = tk.Label(self.common, text = 'Backend Status:')
        self.status_ind   = tk.Canvas(self.common, bg = 'red', height = 10, width = 10)

        # Populate items for the four frontend instances

        self.m_pow_var = []
        self.m_pow = []
        self.m_frame = []
        self.frontend = []

        for i in range(4):
            self.m_pow_var.append(tk.IntVar())
            self.m_frame.append(tk.Frame(self.status_frame))

            cb = tk.Checkbutton(self.m_frame[-1], text = str(i).rjust(2),
                                variable = self.m_pow_var[-1], font = 'TkFixedFont')

            self.m_pow.append(cb)

            fe = self.backend.frontend[i]
            self.frontend.append(FrontendUI(fe, self.m_frame[-1]))

        # Acq elements
        self.data = tk.Text(acq_frame, height = 4, takefocus = False)

    def pack(self):
        self.common.pack(padx = 10, pady = 10)
        self.status_label.pack(side = tk.LEFT, padx = 5, pady = 10)
        self.status_ind.pack(side = tk.LEFT, padx = 5, pady = 10)

        for fr, cb in zip(self.m_frame, self.m_pow):
            fr.pack(fill = tk.BOTH, expand = True)
            cb.pack(side = tk.LEFT)

        self.data.pack(fill = tk.X, side = tk.TOP, padx = 10, pady = 10, expand = True)

