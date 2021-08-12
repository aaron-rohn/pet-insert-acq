import time
import socket
import tkinter as tk

from command import Command
from gigex import Gigex

class Backend():
    def __init__(self, parent_frame, label, ip):
        self.ip = ip
        self.gx = Gigex(ip)

        self.frame  = tk.Frame(parent_frame)
        self.label  = tk.Label(self.frame, text = label + ":")
        self.text   = tk.Label(self.frame, text = ip)
        self.status = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10)

        self.m_pow_var = [tk.IntVar() for _ in range(4)]
        self.m_pow  = [tk.Checkbutton(self.frame, text = i, variable = self.m_pow_var[i]) for i in range(4)]

        self.frame.pack(fill = tk.X, expand = True, padx = 10, pady = 10)
        self.label.pack(side = tk.LEFT)
        self.text.pack(side = tk.LEFT)
        self.status.pack(side = tk.LEFT, padx = 10)
        [m.pack(side = tk.LEFT) for m in self.m_pow]

    def __exec_cmd(self, cmd, *args):
        with self.gx:
            return self.gx.spi_query(cmd(*args))

    def set_status(self):
        cmd_resp = self.__exec_cmd(Command.backend_status, 10)
        value_out = Command.cmd_payload(cmd_resp)
        self.status.config(bg = 'green' if value_out == 10 else 'red')

    def get_rx_status(self):
        cmd_resp = self.__exec_cmd(Command.gpio_rd_rx_err)
        return Command.cmd_payload(cmd_resp) & 0xF

    def get_tx_status(self):
        cmd_resp = self.__exec_cmd(Command.gpio_rd_tx_idle)
        return Command.cmd_payload(cmd_resp) & 0xF

    def get_set_frontend_power(self, update = False):
        """
        pow_state = self.__exec_cmd(Command.set_power, False)
        pow_state = Command.cmd_payload(pow_state) & 0xF

        if update:
            pow_state = [bool(pow_state & (1 << i)) for i in range(4)]
            nxt_state = [m.get() for m in self.m_pow_var]
            pow_off   = [a and not b for (a,b) in zip(pow_state,nxt_state)]

            cmd_resp = self.__exec_cmd(Command.set_power, update, nxt_state)
            pow_state = Command.cmd_payload(cmd_resp)

            if any(pow_off):
                with self.gx:
                    time.sleep(1)
                    self.gx.reboot()
                    time.sleep(1)
        """

        nxt_state = [m.get() for m in self.m_pow_var]
        cmd_resp = self.__exec_cmd(Command.set_power, update, nxt_state)
        return Command.cmd_payload(cmd_resp)

