import os, shutil, time, socket, glob
import numpy as np
import tkinter as tk
from tkinter.ttk import Separator, Notebook
from contextlib import ExitStack

from gigex import NetworkErrors
from frontend import BIAS_ON, BIAS_OFF
from system import System
from sync_ui import SyncUI
from backend_ui import BackendUI
from toggle_button import ToggleButton

class SystemUI():
    def get_status(self):
        self.sys.flush()

        sync_status = self.sys.sync.get_status()
        self.sync.status_ind.config(bg = 'green' if sync_status else 'red')

        # Directly check the status of each backend
        be_status = self.sys.get_status()
        be_status = zip(self.backend, be_status)
        [b.status_ind.config(bg = 'green' if s else 'red') for b,s in be_status]

        # Check the RX status for each port on each backend to infer the frontend state
        sys_rx = self.sys.get_rx_status()
        for be, be_rx in zip(self.backend, sys_rx):
            for fe, err in zip(be.frontend, be_rx):
                fe.status_ind.config(bg = 'red' if err else 'green')

    def enumerate(self):
        sys_idx = self.sys.get_physical_idx()
        for be, be_idx in zip(self.backend, sys_idx):
            for indicator, phys_idx in zip(be.m_pow, be_idx):
                indicator.config(text = str(phys_idx).rjust(2))

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
            tk.messagebox.showerror(message = "Error setting power states")

    def set_power(self):
        states_in = self.get_pwr_vars()
        states_out = self.sys.set_power(states_in)
        if states_out != states_in:
            tk.messagebox.showerror(message = "Error setting power states")

    def toggle_power(self, turn_on = False):
        self.sys.set_power([[turn_on]*4]*4)
        self.get_power()
        self.get_status()

    def toggle_bias(self, turn_on = False):
        val = BIAS_ON if turn_on else BIAS_OFF
        self.sys.set_bias(val)

    def start_acq(self):
        self.sys.set_bias(BIAS_OFF)

        for be in self.backend:
            # X.X.1.X -> /opt/acq1
            # X.X.2.X -> /opt/acq2
            fields = be.ip.split('.')
            idx = int(fields[2]) - 1

            if idx != 0 & idx != 1:
                raise ValueError('IP address must use 1 or 2 in the third field')

            fname = os.path.join(self.data_dirs[idx], be.ip + '.SGL')
            be.acq_start(fname)

        self.acq_start_button.config(state = tk.DISABLED)
        self.acq_stop_button.config(state = tk.NORMAL)

        self.sys.sync.sync_reset()
        time.sleep(1)
        self.sys.set_bias(BIAS_ON)

    def stop_acq(self):
        self.sys.set_bias(BIAS_OFF)

        for be in self.backend:
            be.acq_end()

        self.acq_start_button.config(state = tk.NORMAL)
        self.acq_stop_button.config(state = tk.DISABLED)

        data_dir = tk.filedialog.askdirectory(
                title = "Directory to store data",
                initialdir = "/")

        if not data_dir: return

        sgl_files = []
        for d in self.data_dirs:
            new_files = glob.glob('*.SGL', root_dir = d)
            new_files = [os.path.join(d, f) for f in new_files]
            sgl_files += new_files

        try:
            for f in sgl_files:
                shutil.copy(f, data_dir)
                os.remove(f)
        except PermissionError:
            pass

    def __enter__(self):
        self.sync.set_network_led(clear = False)
        with ExitStack() as stack:
            [stack.enter_context(b) for b in self.backend]
            self._stack = stack.pop_all()

        return self
    
    def __exit__(self, *context):
        self.sync.set_network_led(clear = True)
        self._stack.__exit__(self, *context)

    def quit(self, event):
        if tk.messagebox.askyesno(message = "Exit application?"):
            self.root.destroy()

    def __init__(self, system_instance):
        self.root = tk.Tk()
        self.root.bind('<Escape>', self.quit)

        self.data_dirs = ['/opt/acq1', '/opt/acq2']

        self.sys = system_instance

        self._stack = None

        main_pack_args = {'fill': tk.X, 'side': tk.TOP, 'expand': True, 'padx': 10, 'pady': 5}
        button_pack_args = {'fill': tk.X, 'side': tk.TOP, 'padx': 10, 'pady': 5}

        # Top level notebook container

        self.pages = Notebook(self.root)

        self.status_frame = tk.Frame(self.pages)
        self.command_frame = tk.Frame(self.pages)
        self.acq_frame = tk.Frame(self.pages)

        self.pages.add(self.status_frame, text = "System status")
        self.pages.add(self.command_frame, text = "Commands")
        self.pages.add(self.acq_frame, text = "Acquisition")

        self.pages.pack(fill = tk.BOTH, expand = True)

        # Acquisition page

        self.acq_start_button = tk.Button(self.acq_frame, text = "Start acquisition",
                command = self.start_acq, state = tk.NORMAL)

        self.acq_stop_button = tk.Button(self.acq_frame, text = "Stop acquisition",
                command = self.stop_acq, state = tk.DISABLED)

        self.acq_start_button.pack(**button_pack_args)
        self.acq_stop_button.pack(**button_pack_args)

        # Status page - sync element

        self.sync = SyncUI(self.sys.sync, self.status_frame)
        self.sync.pack()

        # Status page - backend elements

        self.backend_tabs = Notebook(self.status_frame)
        self.backend_tabs.pack(side = tk.TOP, anchor = tk.N,
                padx = 10, pady = 10, fill = tk.BOTH, expand = True)

        self.backend = []

        for be in self.sys.backend:
            bnew = BackendUI(be, self.backend_tabs, self.acq_frame)
            self.backend.append(bnew)
            bnew.pack()

            for fe in bnew.frontend:
                fe.pack()

            self.backend_tabs.add(bnew.status_frame, text = bnew.ip)

        # Main operation buttons

        self.refresh = tk.Button(self.status_frame, text = "Refresh", command = self.get_status)
        self.enum = tk.Button(self.status_frame, text = "Enumerate", command = self.enumerate)
        self.pwr_tog = ToggleButton(self.status_frame, "Power ON", "Power OFF", self.toggle_power)
        self.bias_tog = ToggleButton(self.status_frame, "Bias ON", "Bias OFF", self.toggle_bias)

        self.refresh.pack(**main_pack_args)
        self.enum.pack(**main_pack_args)
        self.pwr_tog.pack(**main_pack_args)
        self.bias_tog.pack(**main_pack_args)

        # Secondary operation buttons

        self.backend_rst = tk.Button(self.command_frame, text = "Backend reset",
                command = lambda: print(self.sys.backend_reset()))

        self.frontend_rst = tk.Button(self.command_frame, text = "Frontend reset",
                command = lambda: print(self.sys.frontend_reset()))

        self.power_rd = tk.Button(self.command_frame, text = "Read power state",
                command = self.get_power)

        self.power_wr = tk.Button(self.command_frame, text = "Set power state",
                command = self.set_power)

        self.current = tk.Button(self.command_frame, text = "Read current",
                command = lambda: print(self.sys.get_current()))

        self.temps = tk.Button(self.command_frame, text = "Read temperature",
                command = lambda: print(self.sys.get_temp()))

        self.bias_rd = tk.Button(self.command_frame, text = "Get bias",
                command = lambda: print(self.sys.get_bias()))

        self.thresh_rd = tk.Button(self.command_frame, text = "Get thresh",
                command = lambda: print(self.sys.get_thresh()))

        self.period_rd = tk.Button(self.command_frame, text = "Get period", 
                command = lambda: print(self.sys.get_period()))

        self.sgl_rate_rd = tk.Button(self.command_frame, text = "Get singles rate",
                command = lambda: print(self.sys.get_all_singles_rates()))

        self.tt_stall = ToggleButton(self.command_frame, "TT Stall ON", "TT Stall OFF",
                lambda s: print(self.sys.tt_stall_disable(s)))

        self.det_disable = ToggleButton(self.command_frame, "Detector ON", "Detector OFF",
                lambda s: print(self.sys.detector_disable(s)))

        self.backend_rst.pack(**button_pack_args)
        self.frontend_rst.pack(**button_pack_args)
        self.power_rd.pack(**button_pack_args)
        self.power_wr.pack(**button_pack_args)
        self.current.pack(**button_pack_args)
        self.temps.pack(**button_pack_args)
        self.bias_rd.pack(**button_pack_args)
        self.thresh_rd.pack(**button_pack_args)
        self.period_rd.pack(**button_pack_args)
        self.sgl_rate_rd.pack(**button_pack_args)
        self.tt_stall.pack(**button_pack_args)
        self.det_disable.pack(**button_pack_args)

if __name__ == "__main__":
    sys = System()
    with SystemUI(sys) as app:
        app.root.mainloop()

