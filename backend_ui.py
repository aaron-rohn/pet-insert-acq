import os, socket, time, queue, threading, logging
import tkinter as tk
from tkinter import filedialog
from frontend_ui import FrontendUI
from backend import BackendAcq

def do_acq(ip, stop, sink, running = None):

    if running is None:
        running = threading.Event()

    with BackendAcq(ip, stop) as acq_inst:
        if isinstance(sink, str):
            logging.info(f'Create new ACQ worker thread to {sink}')
            with open(sink, 'wb') as f:
                running.set()
                for d in acq_inst:
                    f.write(d)

        else:
            logging.info(f'Create new ACQ worker thread to UI')
            running.set()
            for d in acq_inst:
                try:
                    sink.put_nowait(d)
                except queue.Full:
                    pass

class BackendUI():
    def __init__(self, backend_instance, status_frame, acq_frame):
        self.backend = backend_instance
        self.status_frame = tk.Frame(status_frame)

        self.ui_data_interval_ms = 100
        self.ui_data_queue = queue.Queue(maxsize = 10)
        self.data = tk.Text(acq_frame, height = 4, takefocus = False)

        self.ui_mon_interval_ms = 1000
        self.ui_mon_queue = queue.Queue()

        # status indicator and label for backend
        self.common = tk.Frame(self.status_frame)
        self.status_label = tk.Label(self.common, text = 'Backend Status:')
        self.status_ind   = tk.Canvas(self.common, bg = 'red', height = 10, width = 10)

        self.m_pow_var = []
        self.m_pow = []
        self.m_frame = []
        self.frontend = []

        # frontent instance and indicators
        for i in range(4):
            self.m_pow_var.append(tk.IntVar())
            self.m_frame.append(tk.Frame(self.status_frame))

            cb = tk.Checkbutton(self.m_frame[-1], text = str(i).rjust(2),
                                variable = self.m_pow_var[-1], font = 'TkFixedFont')

            self.m_pow.append(cb)

            fe = self.backend.frontend[i]
            self.frontend.append(FrontendUI(fe, self.m_frame[-1]))

    def pack(self):
        self.data.pack(fill = tk.X, side = tk.TOP,
                padx = 10, pady = 10, expand = True)

        self.common.pack(padx = 10, pady = 10)
        self.status_label.pack(side = tk.LEFT, padx = 5, pady = 10)
        self.status_ind.pack(side = tk.LEFT, padx = 5, pady = 10)

        for fr, cb in zip(self.m_frame, self.m_pow):
            fr.pack(fill = tk.BOTH, expand = True)
            cb.pack(side = tk.LEFT)

    def __enter__(self):
        self.exit = threading.Event()
        self.dest = queue.Queue()
        self.cv = threading.Condition()

        self.acq_management_thread = threading.Thread(
                target = self.acq, daemon = False)

        self.monitor_thread = threading.Thread(
                target = self.mon, daemon = True)

        self.acq_management_thread.start()
        self.monitor_thread.start()

        self.common.after(self.ui_mon_interval_ms,
                self.check_mon_queue)
        self.data.after(self.ui_data_interval_ms,
                self.check_data_queue)

        return self

    def __exit__(self, *context):
        self.exit.set()

        with self.cv:
            self.cv.notify_all()

        self.monitor_thread.join()
        self.acq_management_thread.join()

    def acq(self):
        acq_stop = threading.Event()
        acq_thread = threading.Thread(target = do_acq,
                args = [self.backend.ip, acq_stop, self.ui_data_queue])
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

                acq_thread = threading.Thread(target = do_acq,
                        args = [self.backend.ip, acq_stop, *vals])

                acq_thread.start()

        logging.info("Exit acq management thread")

    def mon(self, interval = 10.0):
        while True:
            temps = self.backend.get_all_temps()
            currs = self.backend.get_current()
            self.ui_mon_queue.put_nowait((temps, currs))

            if self.exit.wait(interval):
                break

        logging.info("Exit monitor thread")

    def put(self, val):
        self.dest.put(val)
        with self.cv:
            self.cv.notify_all()

    def check_mon_queue(self):
        if not self.exit.is_set():
            self.common.after(self.ui_mon_interval_ms,
                    self.check_mon_queue)

        try:
            temps, currs = self.ui_mon_queue.get_nowait()
            for fe, t, c in zip(self.frontend, temps, currs):
                fe.set_all_temps(t)
                fe.set_current(c)
        except queue.Empty:
            pass

    def check_data_queue(self):
        if not self.exit.is_set():
            self.data.after(self.ui_data_interval_ms,
                    self.check_data_queue)

        try:
            d = self.ui_data_queue.get_nowait()
            self.data.delete(1.0, 'end')
            self.data.insert('end', str(d) + "\n")
        except queue.Empty:
            pass
