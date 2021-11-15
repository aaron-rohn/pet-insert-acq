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

    def enumerate(self):
        sys_idx = self.sys.get_physical_idx()
        for be, be_idx in zip(self.backend, sys_idx):
            for indicator, phys_idx in zip(be.m_pow, be_idx):
                indicator.config(text = str(phys_idx).rjust(2))

    def get_current(self):
        print(self.sys.get_current())

    def get_temp(self):
        print(self.sys.get_temp())

    def set_pwr_vars(self, states):
        for be, be_state in zip(self.backend, states):
            if be_state is None:
                [var.set(False) for var in be.m_pow_var]
            else:
                [var.set(state) for var,state in zip(be.m_pow_var, be_state)]

    def get_pwr_vars(self):
        return [[var.get() for var in b.m_pow_var] for b in self.backend]

    def get_power(self):
        states_in = self.sys.get_power()
        self.set_pwr_vars(states_in)
        states_out = self.get_pwr_vars()

        if states_out != states_in:
            print("Error getting power states")

        return states_out

    def set_power(self):
        states_in = self.get_pwr_vars()
        states_out = self.sys.set_power(states_in)

        if states_out != states_in:
            print("Error setting power states")

        return states_out

    def power_toggle_cb(self, turn_on = False):
        popup = tk.Toplevel(self.root)
        popup.title('Power on' if turn_on else 'Power off')
        popup.attributes('-type', 'dialog')
        popup_status = tk.Label(popup, text = 'Module: 0')
        popup_status.pack(pady = 20, padx = 20)

        pwr = self.get_power()
        n = 4

        for i in range(n):
            for elem in pwr: elem[i] = turn_on
            new_pwr = self.sys.set_power(pwr)
            [be.flush() for be in self.sys.backend]

            self.set_pwr_vars(new_pwr)
            popup_status.config(text = f'Module: {i}')
            self.root.update()
            time.sleep(1)

        popup.destroy()

        self.get_power()
        self.get_status()

    def bias_toggle_cb(self, turn_on = False):
        if turn_on:
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
        self.power_rd = tk.Button(self.root, text = "Read power state", command = self.get_power)
        self.power_wr = tk.Button(self.root, text = "Set power state", command = self.set_power)
        self.current = tk.Button(self.root, text = "Read current", command = self.get_current)
        self.temps   = tk.Button(self.root, text = "Read temperature", command = self.get_temp)

        pack_args = {'fill': tk.X, 'expand': True, 'padx': 10, 'pady': 10}
        self.refresh.pack(**pack_args)
        self.enum.pack(**pack_args)
        self.power_toggle.pack(**pack_args)
        self.bias_toggle.pack(**pack_args)

        Separator(self.root).pack(fill = tk.X, padx = 10, pady = 20)
        
        self.power_rd.pack(**pack_args)
        self.power_wr.pack(**pack_args)
        self.current.pack(**pack_args)
        self.temps.pack(**pack_args)

        self.root.bind('<Escape>', lambda *args: self.root.quit())

if __name__ == "__main__":
    sys = System()
    app = SystemUI(sys)
    with sys:
        app.root.mainloop()

