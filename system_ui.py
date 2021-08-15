import tkinter as tk
from tkinter.ttk import Separator

from system import System
from backend import Backend
from backend_ui import BackendUI

class SystemUI():
    def print(self, txt):
        self.status_text.insert(tk.END, str(txt) + "\n")
        self.status_text.yview(tk.END)

    def get_status(self):
        status = zip(self.backend, self.sys.get_status())
        [b.status.config(bg = 'green' if s else 'red') for b,s in status]

    def get_set_power(self, update = False):
        states = []
        for b in self.backend:
            states.append([v.get() for v in b.m_pow_var])
        ret = self.sys.get_set_power(update, states)
        self.print(ret)

    def __init__(self, system_instance):
        self.root = tk.Tk()

        self.sys = system_instance
        self.backend = [BackendUI(b, self.root) for b in self.sys.backend]

        self.backend_refresh   = tk.Button(self.root, text = "Refresh", command = self.get_status)
        self.backend_rx_status = tk.Button(self.root, text = "Update RX status", command = lambda: self.print(self.sys.get_rx_status()))
        self.backend_tx_status = tk.Button(self.root, text = "Update TX status", command = lambda: self.print(self.sys.get_tx_status()))
        self.power_rd_callback = tk.Button(self.root, text = "Read power state", command = self.get_set_power)
        self.power_wr_callback = tk.Button(self.root, text = "Set power state", command = lambda: self.get_set_power(True))
        self.current_callback  = tk.Button(self.root, text = "Read current", command = lambda: self.print(self.sys.get_current()))

        self.backend_refresh.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.backend_rx_status.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.backend_tx_status.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.power_rd_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.power_wr_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.current_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)

        Separator(self.root, orient = "horizontal").pack(fill = tk.X, expand = True, padx = 10, pady = 10)

        self.status_text = tk.Text(master = self.root, width = 60, height = 20, takefocus = False)
        self.status_text.pack(fill = "both", expand = True, padx = 10, pady = 10)

if __name__ == "__main__":
    sys = System()
    app = SystemUI(sys)
    with sys:
        app.root.mainloop()

