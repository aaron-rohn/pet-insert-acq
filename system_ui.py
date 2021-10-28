import time
import numpy as np
import tkinter as tk
from tkinter.ttk import Separator

from system import System
from sync_ui import SyncUI
from backend_ui import BackendUI
from toggle_button import ToggleButton

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
                fe.status.config(bg = 'red' if err else 'green')

    def get_set_power(self, update = False):
        states = []
        for b in self.backend:
            states.append([v.get() for v in b.m_pow_var])
        states = self.sys.get_set_power(update, states)
        print(states)
        return states

    def enumerate(self):
        sys_idx = self.sys.get_physical_idx()
        for be, be_idx in zip(self.backend, sys_idx):
            for indicator, phys_idx in zip(be.m_pow, be_idx):
                indicator.config(text = phys_idx)

    def get_current(self):
        print(self.sys.get_current())

    def update_pwr_states(self):
        pwr_states = self.get_set_power()
        for b,s_all in zip(self.backend, pwr_states):
            [v.set(s) for v,s in zip(b.m_pow_var, s_all)]

    def power_toggle_cb(self, turn_on = False):
        if turn_on:
            """
            popup = tk.Toplevel(self.root)
            popup.title('Power on')
            popup.attributes('-type', 'dialog')
            popup_status = tk.Label(popup, text = 'Module: 0')
            popup_status.pack(pady = 20, padx = 20)

            for i in range(1,5):
                pwr = [True]*i + [False]*(4-i)
                self.sys.get_set_power(True, [pwr]*4)
                popup_status.config(text = f'Module: {i}')

                time.sleep(1)
                self.update_pwr_states()

            popup.destroy()
            """
            self.sys.get_set_power(True, [[True]*4]*4)
        else:
            self.sys.get_set_power(True, [[False]*4]*4)

        self.update_pwr_states()
        self.get_status()

    def bias_toggle_cb(self, turn_on = False):
        if turn_on:
            """
            popup = tk.Toplevel(self.root)
            popup.title('Bias on')
            popup.attributes('-type', 'dialog')
            popup_status = tk.Label(popup, text = 'Bias: 0.0')
            popup_status.pack(pady = 20, padx = 20)

            vals = np.linspace(0.0, 29.5, 5)
            for v in vals:
                self.sys.set_bias(v)
                popup_status.config(text = f'Bias: {round(v,1)}')
                time.sleep(1)

            popup.destroy()
            """
            self.sys.set_bias(29.5)
        else:
            self.sys.set_bias(0.0)

    def __init__(self, system_instance):
        self.root = tk.Tk()

        self.sys = system_instance
        self.sync = SyncUI(self.sys.sync, self.root)
        self.backend = [BackendUI(b, self.root) for b in self.sys.backend]

        self.refresh = tk.Button(self.root, text = "Refresh", command = self.get_status)
        self.enum = tk.Button(self.root, text = "Enumerate", command = self.enumerate)
        self.power_toggle = ToggleButton(self.root, "Power ON", "Power OFF", self.power_toggle_cb)
        self.bias_toggle = ToggleButton(self.root, "Bias ON", "Bias OFF", self.bias_toggle_cb)
        self.power_rd = tk.Button(self.root, text = "Read power state", command = self.get_set_power)
        self.power_wr = tk.Button(self.root, text = "Set power state", command = lambda: self.get_set_power(True))
        self.current = tk.Button(self.root, text = "Read current", command = self.get_current)

        pack_args = {'fill': tk.X, 'expand': True, 'padx': 10, 'pady': 10}
        self.refresh.pack(**pack_args)
        self.enum.pack(**pack_args)
        self.power_toggle.pack(**pack_args)
        self.bias_toggle.pack(**pack_args)

        Separator(self.root).pack(fill = tk.X, padx = 10, pady = 20)
        
        self.power_rd.pack(**pack_args)
        self.power_wr.pack(**pack_args)
        self.current.pack(**pack_args)

        self.root.bind('<Escape>', lambda *args: self.root.quit())

if __name__ == "__main__":
    sys = System()
    app = SystemUI(sys)
    with sys:
        app.root.mainloop()

