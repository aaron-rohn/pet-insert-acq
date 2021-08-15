import tkinter as tk
from tkinter.ttk import Separator

from system import System
from backend_ui import BackendUI

class SystemUI():
    def print(self, txt):
        self.status_text.insert(tk.END, str(txt) + "\n")
        self.status_text.yview(tk.END)

    def get_status(self):
        # Directly check the status of each backend
        be_status = self.sys.get_status()
        be_status = zip(self.backend, be_status)
        [b.status.config(bg = 'green' if s else 'red') for b,s in be_status]

        # Check the RX status for each port on each backend to infer the frontend state
        sys_rx = self.sys.get_rx_status()
        for be, be_rx in zip(self.backend, sys_rx):
            for fe, err in zip(be.frontend, be_rx):
                fe.status.config(bg = 'green' if not err else 'red')

    def get_set_power(self, update = False):
        states = []
        for b in self.backend:
            states.append([v.get() for v in b.m_pow_var])
        ret = self.sys.get_set_power(update, states)
        self.print(ret)

    def enumerate(self):
        sys_idx = self.sys.get_physical_idx()
        for be, be_idx in zip(self.backend, sys_idx):
            for indicator, phys_idx in zip(be.m_pow, be_idx):
                indicator.config(text = phys_idx)

    def __init__(self, system_instance):
        self.root = tk.Tk()

        self.sys = system_instance
        self.backend = [BackendUI(b, self.root) for b in self.sys.backend]

        self.refresh = tk.Button(self.root, text = "Refresh", command = self.get_status)
        self.enum = tk.Button(self.root, text = "Enumerate", command = self.enumerate)
        self.power_rd_callback = tk.Button(self.root, text = "Read power state", command = self.get_set_power)
        self.power_wr_callback = tk.Button(self.root, text = "Set power state", command = lambda: self.get_set_power(True))
        self.current_callback  = tk.Button(self.root, text = "Read current", command = lambda: self.print(self.sys.get_current()))

        self.refresh.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.enum.pack(fill = "both", expand = True, padx = 10, pady = 10)
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

