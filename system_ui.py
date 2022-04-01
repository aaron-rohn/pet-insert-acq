import logging, threading, queue
import tkinter.filedialog
import tkinter as tk
from tkinter.ttk import Separator, Notebook
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

    # UI only methods

    def statusbar_status_handler(self, status):
        self.statusbar_label.config(text = 'Status: {}'.format('OK' if status else 'ERROR'))

    def statusbar_enum_handler(self, status):
        self.statusbar_enum.config(text = 'Enum: {}'.format('OK' if status else 'ERROR'))

    def statusbar_power_handler(self, power):
        self.statusbar_power_label.config(text = 'Power: {}'.format('ON' if power else 'OFF'))

    def statusbar_bias_handler(self, bias):
        self.statusbar_bias_label.config(text = 'Bias: {}'.format('ON' if bias else 'OFF'))

    def statusbar_acq_handler(self, running):
        self.statusbar_acq_label.config(text = 'Acq: {}'.format('RUN' if running else 'STOP'))

    def cmd_output_print(self, value):
        self.cmd_output.delete(1.0, 'end')
        self.cmd_output.insert('end', str(value) + "\n")

    def set_pwr_vars(self, states):
        for be, be_state in zip(self.backend, states):
            if be_state is None:
                [var.set(False) for var in be.m_pow_var]
            else:
                [var.set(state) for var,state in zip(be.m_pow_var, be_state)]

    def get_pwr_vars(self):
        return [[var.get() for var in b.m_pow_var] for b in self.backend]

    def quit(self, event):
        if tk.messagebox.askyesno(message = "Exit application?"):
            self.root.destroy()

    # Methods that interact with the system

    def get_status(self):
        self.refresh.config(state = tk.DISABLED)
        data_queue = queue.Queue()
        stat_thread = threading.Thread(
                target = self.sys.sys_status,
                args = [data_queue])

        def status_check():
            if data_queue.empty():
                self.root.after(100, status_check)
            else:
                sync_status, be_status, sys_pwr, sys_enum = data_queue.get()

                sys_status = sync_status and all(be_status)
                col = 'green' if sync_status else 'red'
                self.sync.status_ind.config(bg = col)

                for be, status in zip(self.backend, be_status):
                    col = 'green' if status else 'red'
                    be.status_ind.config(bg = col)

                enum_status = True
                for be, be_enum, be_pwr in zip(self.backend, sys_enum, sys_pwr):
                    for indicator, fe_enum, fe_pwr in zip(be.m_pow, be_enum, be_pwr):
                        enum_status &= (fe_enum != -1 or not fe_pwr)
                        indicator.config(text = str(fe_enum).rjust(2))

                self.statusbar_status_handler(sys_status)
                self.statusbar_enum_handler(enum_status)
                self.refresh.config(state = tk.NORMAL)

        stat_thread.start()
        status_check()

    def get_power(self):
        # TODO move to background thread
        states_in = self.sys.get_power()
        self.set_pwr_vars(states_in)
        states_out = self.get_pwr_vars()
        if states_out != states_in:
            tk.messagebox.showerror(message = "Error setting power states")

    def set_power(self):
        # TODO move to background thread
        states_in = self.get_pwr_vars()
        states_out = self.sys.set_power(states_in)
        if states_out != states_in:
            tk.messagebox.showerror(message = "Error setting power states")

    def toggle_bias(self, turn_on = False):
        # TODO move to background thread
        val = BIAS_ON if turn_on else BIAS_OFF
        self.sys.set_bias(val)
        self.statusbar_bias_handler(turn_on)

    def toggle_power(self, turn_on = False):
        nmodules = 4
        popup = PowerPopup(self.root, turn_on)
        self.pwr_tog.config(state = tk.DISABLED)
        starting_pwr = self.sys.get_power()

        def set_next_pwr(pwr, i):
            if i < nmodules:
                for p in pwr: p[i] = turn_on
                new_pwr = self.sys.set_power(pwr)
                self.set_pwr_vars(new_pwr)
                popup.set(i)
                popup.after(1000, set_next_pwr, pwr, i + 1)
            else:
                popup.destroy()
                self.pwr_tog.config(state = tk.NORMAL)
                self.statusbar_power_handler(turn_on)
                self.get_status()

        set_next_pwr(starting_pwr, 0)

    def start_acq(self):
        self.acq_start_button.config(state = tk.DISABLED)
        finished = threading.Event()

        def acq_check_fun():
            if finished.is_set():
                self.acq_stop_button.config(state = tk.NORMAL)
                self.statusbar_acq_handler(True)
            else:
                self.root.after(100, acq_check_fun)

        acq_start_thread = threading.Thread(
                target = self.sys.acq_start,
                args = [finished])

        acq_start_thread.start()
        acq_check_fun()

    def stop_acq(self):
        finished = threading.Event()
        self.acq_stop_button.config(state = tk.DISABLED)
        data_dir = tk.filedialog.askdirectory(
                title = "Directory to store data",
                initialdir = "/")

        def acq_check_fun():
            if finished.is_set():
                self.acq_start_button.config(state = tk.NORMAL)
                self.statusbar_acq_handler(False)
            else:
                self.root.after(100, acq_check_fun)

        acq_stop_thread = threading.Thread(
                target = self.sys.acq_stop,
                args = [finished, data_dir])

        acq_stop_thread.start()
        acq_check_fun()

    # Instantiate the UI

    def __init__(self, system_instance):
        self.root = tk.Tk()
        self.root.bind('<Escape>', self.quit)
        self.sys = system_instance

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
        self.statusbar_enum = tk.Label(self.statusbar_frame)
        self.statusbar_power_label = tk.Label(self.statusbar_frame)
        self.statusbar_bias_label = tk.Label(self.statusbar_frame)
        self.statusbar_acq_label = tk.Label(self.statusbar_frame)

        self.statusbar_label.pack(side = tk.LEFT, padx = 5)
        self.statusbar_enum.pack(side = tk.LEFT, padx = 5)
        self.statusbar_power_label.pack(side = tk.LEFT, padx = 5)
        self.statusbar_bias_label.pack(side = tk.LEFT, padx = 5)
        self.statusbar_acq_label.pack(side = tk.LEFT, padx = 5)

        self.statusbar_status_handler(False)
        self.statusbar_enum_handler(False)
        self.statusbar_power_handler(False)
        self.statusbar_bias_handler(False)
        self.statusbar_acq_handler(False)

        # Acquisition page

        self.acq_start_button = tk.Button(self.acq_frame, text = "Start acquisition",
                command = self.start_acq, state = tk.NORMAL)

        self.acq_stop_button = tk.Button(self.acq_frame, text = "Stop acquisition",
                command = self.stop_acq, state = tk.DISABLED)

        button_pack_args = {'fill': tk.X, 'side': tk.TOP, 'padx': 10, 'pady': 5}

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
        self.pwr_tog = ToggleButton(self.status_frame, "Power ON", "Power OFF", self.toggle_power)
        self.bias_tog = ToggleButton(self.status_frame, "Bias ON", "Bias OFF", self.toggle_bias)

        self.power_rd = tk.Button(self.status_frame, text = "Read power state",
                command = self.get_power)

        self.power_wr = tk.Button(self.status_frame, text = "Set power state",
                command = self.set_power)

        main_pack_args = {'fill': tk.X, 'side': tk.TOP, 'expand': True, 'padx': 10, 'pady': 5}
        self.refresh.pack(**main_pack_args)
        self.pwr_tog.pack(**main_pack_args)
        self.bias_tog.pack(**main_pack_args)
        Separator(self.status_frame).pack(fill = tk.X, padx = 60, pady = 30)
        self.power_rd.pack(**main_pack_args)
        self.power_wr.pack(**main_pack_args)

        # Command page - Secondary operation buttons

        self.backend_rst_soft = tk.Button(self.command_frame, text = "Backend reset soft",
                command = lambda: self.cmd_output_print(self.sys.backend_reset_soft()))

        self.backend_rst_hard = tk.Button(self.command_frame, text = "Backend reset hard",
                command = lambda: self.cmd_output_print(self.sys.backend_reset_hard()))

        self.frontend_rst = tk.Button(self.command_frame, text = "Frontend reset",
                command = lambda: self.cmd_output_print(self.sys.frontend_reset()))

        self.current = tk.Button(self.command_frame, text = "Read current",
                command = lambda: self.cmd_output_print(self.sys.get_current()))

        self.temps = tk.Button(self.command_frame, text = "Read temperature",
                command = lambda: self.cmd_output_print(self.sys.get_all_temps()))

        self.be_sgl_rate_rd = tk.Button(self.command_frame, text = "Read backend singles rate",
                command = lambda: self.cmd_output_print(self.sys.get_counter(0)))
        self.be_tt_rate_rd  = tk.Button(self.command_frame, text = "Read backend time tag rate",
                command = lambda: self.cmd_output_print(self.sys.get_counter(1)))
        self.be_cmd_rate_rd = tk.Button(self.command_frame, text = "Read backend command rate",
                command = lambda: self.cmd_output_print(self.sys.get_counter(2)))

        self.bias_rd = tk.Button(self.command_frame, text = "Read bias",
                command = lambda: self.cmd_output_print(self.sys.get_bias()))

        self.thresh_rd = tk.Button(self.command_frame, text = "Read thresh",
                command = lambda: self.cmd_output_print(self.sys.get_thresh()))

        self.period_rd = tk.Button(self.command_frame, text = "Read period", 
                command = lambda: self.cmd_output_print(self.sys.get_period()))

        self.sgl_rate_rd = tk.Button(self.command_frame, text = "Read frontend singles rate",
                command = lambda: self.cmd_output_print(self.sys.get_all_singles_rates()))

        self.tt_stall = ToggleButton(self.command_frame, "TT Stall ON", "TT Stall OFF",
                lambda s: self.cmd_output_print(self.sys.tt_stall_disable(s)))

        self.det_disable = ToggleButton(self.command_frame, "Detector ON", "Detector OFF",
                lambda s: self.cmd_output_print(self.sys.detector_disable(s)))

        self.backend_rst_soft.pack(**button_pack_args)
        self.backend_rst_hard.pack(**button_pack_args)
        self.frontend_rst.pack(**button_pack_args)
        self.current.pack(**button_pack_args)
        self.temps.pack(**button_pack_args)
        self.be_sgl_rate_rd.pack(**button_pack_args)
        self.be_tt_rate_rd.pack(**button_pack_args)
        self.be_cmd_rate_rd.pack(**button_pack_args)

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
    app = SystemUI(sys)
    with sys:
        app.root.mainloop()

