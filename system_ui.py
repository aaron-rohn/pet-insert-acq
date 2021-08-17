import tkinter as tk
from tkinter.ttk import Separator
from tkinter import filedialog

from system import System
from sync_ui import SyncUI
from backend_ui import BackendUI

class SystemUI():
    def get_status(self):
        sync_status = self.sys.sync.get_status()
        self.sync.status.config(bg = 'green' if sync_status else 'red')

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
        print(self.sys.get_set_power(update, states))

    def enumerate(self):
        sys_idx = self.sys.get_physical_idx()
        for be, be_idx in zip(self.backend, sys_idx):
            for indicator, phys_idx in zip(be.m_pow, be_idx):
                indicator.config(text = phys_idx)

    def update_output_dir(self):
        dirname = filedialog.askdirectory()
        self.file_indicator.config(text = dirname)

    def __init__(self, system_instance):
        self.root = tk.Tk()

        self.sys = system_instance
        self.sync = SyncUI(self.sys.sync, self.root)
        self.backend = [BackendUI(b, self.root) for b in self.sys.backend]

        self.file_output = tk.Frame(self.root)
        self.file_select = tk.Button(self.file_output, text = "Directory", command = self.update_output_dir)
        self.file_indicator = tk.Label(self.file_output, bg = 'white', text = '', anchor = 'w', relief = tk.SUNKEN, borderwidth = 1, height = 2) 
        self.file_output.pack(fill = tk.X, expand = True)
        self.file_select.pack(side = tk.LEFT, padx = 10, pady = 10)
        self.file_indicator.pack(side = tk.LEFT, fill = tk.X, expand = True, padx = 10, pady = 10)

        self.refresh = tk.Button(self.root, text = "Refresh", command = self.get_status)
        self.enum = tk.Button(self.root, text = "Enumerate", command = self.enumerate)
        self.power_rd_callback = tk.Button(self.root, text = "Read power state", command = self.get_set_power)
        self.power_wr_callback = tk.Button(self.root, text = "Set power state", command = lambda: self.get_set_power(True))
        self.current_callback  = tk.Button(self.root, text = "Read current", command = self.sys.get_current)

        self.refresh.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.enum.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.power_rd_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.power_wr_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.current_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)

        Separator(self.root, orient = "horizontal").pack(fill = tk.X, expand = True, padx = 10, pady = 10)

        self.status_text = tk.Text(master = self.root, width = 60, height = 20, takefocus = False)
        self.status_text.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.root.bind('<Escape>', lambda *args: self.root.quit())

if __name__ == "__main__":
    sys = System()
    app = SystemUI(sys)
    with sys:
        app.root.mainloop()

