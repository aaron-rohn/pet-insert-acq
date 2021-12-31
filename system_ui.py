import os, shutil, time, glob, logging, threading
import numpy as np
import tkinter as tk
from tkinter.ttk import Separator, Notebook
from contextlib import ExitStack
from frontend import BIAS_ON, BIAS_OFF
from system import System
from sync_ui import SyncUI
from backend_ui import BackendUI
from toggle_button import ToggleButton

class PowerPopup(tk.Toplevel):
    def __init__(self, root, turn_on):
        super().__init__(root)
        self.title('Power on' if turn_on else 'Power off')
        self.attributes('-type', 'dialog')
        self.popup_status = tk.Label(self, text = 'Module: 0')
        self.popup_status.pack(pady = 20, padx = 40)

    def set(self, i):
        self.popup_status.config(text = f'Module: {i}')

class SystemUI():
    def statusbar_status_handler(self, status):
        self.statusbar_label.config(text = 'Status: {}'.format('OK' if status else 'ERROR'))

    def statusbar_power_handler(self, power):
        self.statusbar_power_label.config(text = 'Power: {}'.format('ON' if power else 'OFF'))

    def statusbar_bias_handler(self, bias):
        self.statusbar_bias_label.config(text = 'Bias: {}'.format('ON' if bias else 'OFF'))

    def statusbar_acq_handler(self, running):
        self.statusbar_acq_label.config(text = 'Acq: {}'.format('RUN' if running else 'STOP'))

    def cmd_output_print(self, value):
        self.cmd_output.delete(1.0, 'end')
        self.cmd_output.insert('end', str(value) + "\n")

    def get_status(self):
        self.sys.flush()
        sys_status = True

        sync_status = self.sys.sync.get_status()
        sys_status &= sync_status
        self.sync.status_ind.config(bg = 'green' if sync_status else 'red')

        # Directly check the status of each backend
        be_status = self.sys.get_status()
        sys_status &= all(be_status)

        for b,s in zip(self.backend, be_status):
            b.status_ind.config(bg = 'green' if s else 'red')

        # Check the RX status for each port on each backend to infer the frontend state
        pwr = self.get_pwr_vars()
        sys_rx = self.sys.get_rx_status()
        for be, be_rx, be_pwr in zip(self.backend, sys_rx, pwr):
            for fe, err, fe_pwr in zip(be.frontend, be_rx, be_pwr):
                sys_status &= (not err or not fe_pwr)
                fe.status_ind.config(bg = 'red' if err else 'green')

        self.statusbar_status_handler(sys_status)

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

    def toggle_power_start(self, turn_on = False):
        self.pwr_tog.config(state = tk.DISABLED)
        popup = PowerPopup(self.root, turn_on)
        pwr = self.sys.get_power()
        self.toggle_power_next(popup, pwr, 0, turn_on)

    def toggle_power_next(self, popup, pwr, i, turn_on):
        if i < 4:
            for elem in pwr:
                elem[i] = turn_on

            new_pwr = self.sys.set_power(pwr)
            [be.flush() for be in self.sys.backend]

            self.set_pwr_vars(new_pwr)
            popup.set(i)

            popup.after(1000, self.toggle_power_next,
                    popup, pwr, i + 1, turn_on)

        else:
            popup.destroy()
            self.pwr_tog.config(state = tk.NORMAL)
            self.statusbar_power_handler(turn_on)

            self.get_status()
            self.enumerate()

    def toggle_bias(self, turn_on = False):
        val = BIAS_ON if turn_on else BIAS_OFF
        self.sys.set_bias(val)
        self.statusbar_bias_handler(turn_on)

    def start_acq(self):
        self.acq_start_button.config(state = tk.DISABLED)
        finished = threading.Event()

        def acq_start_fun():
            self.sys.detector_disable(True)
            time.sleep(1)

            all_running = []
            for be in self.backend:
                # X.X.1.X -> /opt/acq1, X.X.2.X -> /opt/acq2
                ip = be.backend.ip
                idx = int(ip.split('.')[2]) - 1
                fname = os.path.join(self.data_dirs[idx], ip + '.SGL')

                running = threading.Event()
                all_running.append(running)
                be.put((fname, running))

            for running in all_running:
                running.wait()

            self.sys.sync.sync_reset()
            self.sys.detector_disable(False)
            finished.set()

        def acq_check_fun():
            if finished.is_set():
                self.acq_stop_button.config(state = tk.NORMAL)
                self.statusbar_acq_handler(True)
            else:
                self.root.after(100, acq_check_fun)

        acq_start_thread = threading.Thread(target = acq_start_fun)
        acq_start_thread.start()
        acq_check_fun()

    def stop_acq(self):
        finished = threading.Event()
        self.acq_stop_button.config(state = tk.DISABLED)
        data_dir = tk.filedialog.askdirectory(
                title = "Directory to store data",
                initialdir = "/")

        def acq_stop_fun():
            self.sys.detector_disable(True)

            ev = []
            for be in self.backend:
                e = threading.Event()
                ev.append(e)
                be.put((be.ui_data_queue, e))

            for e in ev:
                e.wait()

            if data_dir:
                sgl_files = []
                for d in self.data_dirs:
                    new_files = glob.glob('*.SGL', root_dir = d)
                    new_files = [os.path.join(d, f) for f in new_files]
                    sgl_files += new_files

                try:
                    for f in sgl_files:
                        shutil.copy(f, data_dir)
                        os.remove(f)
                except PermissionError as e:
                    logging.warning('Failed to move acquition files', exc_info = e)

            finished.set()

        def acq_check_fun():
            if finished.is_set():
                self.acq_start_button.config(state = tk.NORMAL)
                self.statusbar_acq_handler(False)
            else:
                self.root.after(100, acq_check_fun)

        acq_stop_thread = threading.Thread(target = acq_stop_fun)
        acq_stop_thread.start()
        acq_check_fun()

    def __enter__(self):
        logging.info("SystemUI enter context")
        self.sys.sync.set_network_led(clear = False)
        with ExitStack() as stack:
            [stack.enter_context(b) for b in self.backend]
            self._stack = stack.pop_all()

        return self
    
    def __exit__(self, *context):
        self.sys.sync.set_network_led(clear = True)
        self._stack.__exit__(self, *context)
        logging.info("SystemUI exit context")

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

        # Status bar

        self.statusbar_frame = tk.Frame(self.root, relief = tk.SUNKEN)
        self.statusbar_frame.pack(side = tk.BOTTOM, fill = tk.X)

        self.statusbar_label = tk.Label(self.statusbar_frame)
        self.statusbar_power_label = tk.Label(self.statusbar_frame)
        self.statusbar_bias_label = tk.Label(self.statusbar_frame)
        self.statusbar_acq_label = tk.Label(self.statusbar_frame)

        self.statusbar_label.pack(side = tk.LEFT, padx = 5)
        self.statusbar_power_label.pack(side = tk.LEFT, padx = 5)
        self.statusbar_bias_label.pack(side = tk.LEFT, padx = 5)
        self.statusbar_acq_label.pack(side = tk.LEFT, padx = 5)

        self.statusbar_status_handler(False)
        self.statusbar_power_handler(False)
        self.statusbar_bias_handler(False)
        self.statusbar_acq_handler(False)

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

            self.backend_tabs.add(bnew.status_frame, text = be.ip)

        # Status page - Main operation buttons

        self.refresh = tk.Button(self.status_frame, text = "Refresh", command = self.get_status)
        self.enum = tk.Button(self.status_frame, text = "Enumerate", command = self.enumerate)
        self.pwr_tog = ToggleButton(self.status_frame, "Power ON", "Power OFF", self.toggle_power_start)
        self.bias_tog = ToggleButton(self.status_frame, "Bias ON", "Bias OFF", self.toggle_bias)

        self.refresh.pack(**main_pack_args)
        self.enum.pack(**main_pack_args)
        self.pwr_tog.pack(**main_pack_args)
        self.bias_tog.pack(**main_pack_args)

        # Command page - Secondary operation buttons

        self.backend_rst = tk.Button(self.command_frame, text = "Backend reset",
                command = lambda: self.cmd_output_print(self.sys.backend_reset()))

        self.frontend_rst = tk.Button(self.command_frame, text = "Frontend reset",
                command = lambda: self.cmd_output_print(self.sys.frontend_reset()))

        self.power_rd = tk.Button(self.command_frame, text = "Read power state",
                command = self.get_power)

        self.power_wr = tk.Button(self.command_frame, text = "Set power state",
                command = self.set_power)

        self.current = tk.Button(self.command_frame, text = "Read current",
                command = lambda: self.cmd_output_print(self.sys.get_current()))

        self.temps = tk.Button(self.command_frame, text = "Read temperature",
                command = lambda: self.cmd_output_print(self.sys.get_all_temps()))

        self.bias_rd = tk.Button(self.command_frame, text = "Read bias",
                command = lambda: self.cmd_output_print(self.sys.get_bias()))

        self.thresh_rd = tk.Button(self.command_frame, text = "Read thresh",
                command = lambda: self.cmd_output_print(self.sys.get_thresh()))

        self.period_rd = tk.Button(self.command_frame, text = "Read period", 
                command = lambda: self.cmd_output_print(self.sys.get_period()))

        self.sgl_rate_rd = tk.Button(self.command_frame, text = "Read singles rate",
                command = lambda: self.cmd_output_print(self.sys.get_all_singles_rates()))

        self.tt_stall = ToggleButton(self.command_frame, "TT Stall ON", "TT Stall OFF",
                lambda s: self.cmd_output_print(self.sys.tt_stall_disable(s)))

        self.det_disable = ToggleButton(self.command_frame, "Detector ON", "Detector OFF",
                lambda s: self.cmd_output_print(self.sys.detector_disable(s)))

        self.backend_rst.pack(**button_pack_args)
        self.frontend_rst.pack(**button_pack_args)
        self.power_rd.pack(**button_pack_args)
        self.power_wr.pack(**button_pack_args)
        self.current.pack(**button_pack_args)
        self.temps.pack(**button_pack_args)

        Separator(self.command_frame).pack(fill = tk.X, padx = 60, pady = 30)

        self.bias_rd.pack(**button_pack_args)
        self.thresh_rd.pack(**button_pack_args)
        self.period_rd.pack(**button_pack_args)
        self.sgl_rate_rd.pack(**button_pack_args)
        self.tt_stall.pack(**button_pack_args)
        self.det_disable.pack(**button_pack_args)

        self.cmd_output = tk.Text(self.command_frame, height = 10, takefocus = False)
        self.cmd_output.pack(**button_pack_args)

        self.get_status()

if __name__ == "__main__":
    logging.basicConfig(level = logging.INFO)
    sys = System()
    with SystemUI(sys) as app:
        app.root.mainloop()

