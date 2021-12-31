import queue
import tkinter as tk
from frontend_ui import FrontendUI

class BackendUI():
    def __init__(self, backend_instance, status_frame, acq_frame):
        self.backend = backend_instance
        self.status_frame = tk.Frame(status_frame)

        self.ui_data_interval_ms = 100
        self.ui_mon_interval_ms = 1000
        self.data = tk.Text(acq_frame, height = 4, takefocus = False)

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

        self.check_mon_queue()
        self.check_data_queue()

    def pack(self):
        self.data.pack(fill = tk.X, side = tk.TOP,
                padx = 10, pady = 10, expand = True)

        self.common.pack(padx = 10, pady = 10)
        self.status_label.pack(side = tk.LEFT, padx = 5, pady = 10)
        self.status_ind.pack(side = tk.LEFT, padx = 5, pady = 10)

        for fr, cb in zip(self.m_frame, self.m_pow):
            fr.pack(fill = tk.BOTH, expand = True)
            cb.pack(side = tk.LEFT)

    def check_mon_queue(self):
        if not self.backend.exit.is_set():
            self.common.after(self.ui_mon_interval_ms,
                    self.check_mon_queue)

        try:
            temps, currs = self.backend.ui_mon_queue.get_nowait()
            for fe, t, c in zip(self.frontend, temps, currs):
                fe.set_all_temps(t)
                fe.set_current(c)
        except queue.Empty: pass

    def check_data_queue(self):
        if not self.backend.exit.is_set():
            self.data.after(self.ui_data_interval_ms,
                    self.check_data_queue)

        try:
            d = self.backend.ui_data_queue.get_nowait()
            self.data.delete(1.0, 'end')
            self.data.insert('end', str(d) + "\n")
        except queue.Empty: pass
