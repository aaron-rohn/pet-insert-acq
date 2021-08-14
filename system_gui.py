import tkinter as tk
from tkinter.ttk import Separator
from tkinter.scrolledtext import ScrolledText

from system import System
from backend import Backend

def to_mask(num):
    return format(num, '#06b')

class BackendUI():
    def __init__(self, backend_instance, parent_frame):
        self.backend = backend_instance
        self.m_pow_var = [tk.IntVar() for _ in range(4)]

        self.frame  = tk.Frame(parent_frame)
        self.label  = tk.Label(self.frame, text = self.backend.label_text+ ":")
        self.text   = tk.Label(self.frame, text = self.backend.ip)
        self.status = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10)
        self.m_pow  = [tk.Checkbutton(self.frame, text = i, variable = self.m_pow_var[i]) for i in range(4)]
        self.data = ScrolledText(master = self.frame, width = 30, height = 5, takefocus = False)

        self.frame.pack(fill = tk.X, expand = True, padx = 10, pady = 10)
        self.label.pack(side = tk.LEFT)
        self.text.pack(side = tk.LEFT)
        self.status.pack(side = tk.LEFT, padx = 10)
        [m.pack(side = tk.LEFT) for m in self.m_pow]
        self.data.pack(side = tk.LEFT, padx = 10)

    def __getattr__(self, attr):
        return getattr(self.backend, attr)

class SystemUI():
    def print(self, txt):
        self.status_text.insert(tk.END, str(txt) + "\n")
        self.status_text.yview(tk.END)

    def __init__(self, root, system_instance):
        self.root = root

        self.sys = system_instance
        self.backend = [BackendUI(b, root) for b in self.sys.backend]

        def refresh_callback():
            ret = [b.set_status() for b in self.backend]
            [b.status.config(bg = 'green' if r else 'red') for b,r in zip(self.backend, ret)]

        self.backend_refresh = tk.Button(self.root, text = "Refresh", command = refresh_callback)
        self.backend_refresh.pack(fill = "both", expand = True, padx = 10, pady = 10)

        def callback_gen(func, *args):
            return lambda: self.print([to_mask(getattr(b, func)(*args)) for b in self.backend])

        def power_callback_gen(update):
            def cb():
                ret = []
                for b in self.backend:
                    nxt_state = [v.get() for v in b.m_pow_var]
                    r = b.get_set_frontend_power(update, nxt_state)
                    ret.append(to_mask(r))
                self.print(ret)
            return cb

        rx_status_callback = callback_gen('get_rx_status')
        tx_status_callback = callback_gen('get_tx_status')
        power_rd_callback  = power_callback_gen(False)
        power_wr_callback  = power_callback_gen(True)
        current_callback   = lambda: self.print([b.get_current() for b in self.backend])

        self.backend_rx_status = tk.Button(self.root, text = "Update RX status", command = rx_status_callback)
        self.backend_tx_status = tk.Button(self.root, text = "Update TX status", command = tx_status_callback)
        self.power_rd_callback = tk.Button(self.root, text = "Read power state", command = power_rd_callback)
        self.power_wr_callback = tk.Button(self.root, text = "Set power state", command = power_wr_callback)
        self.current_callback  = tk.Button(self.root, text = "Read current", command = current_callback)

        self.backend_rx_status.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.backend_tx_status.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.power_rd_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.power_wr_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.current_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)

        Separator(self.root, orient = "horizontal").pack(fill = tk.X, expand = True, padx = 10, pady = 10)

        self.status_text = ScrolledText(master = self.root, width = 60, height = 20, takefocus = False)
        self.status_text.pack(fill = "both", expand = True, padx = 10, pady = 10)

with System() as sys:
    root = tk.Tk()
    app = SystemUI(root, sys)
    root.mainloop()
