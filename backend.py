import time
import socket
import tkinter as tk

import command as cmd
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

    def __exec_cmd(self, cmd_int):
        with self.gx:
            return self.gx.spi_query(cmd_int)

    def set_status(self):
        resp = self.__exec_cmd(cmd.backend_status(10))
        value_out = cmd.payload(resp)
        self.status.config(bg = 'green' if value_out == 10 else 'red')

    def get_rx_status(self):
        resp = self.__exec_cmd(cmd.gpio_rd_rx_err())
        return cmd.payload(resp) & 0xF

    def get_tx_status(self):
        resp = self.__exec_cmd(cmd.gpio_rd_tx_idle())
        return cmd.payload(resp) & 0xF

    def get_set_frontend_power(self, update = False):
        nxt_state = [m.get() for m in self.m_pow_var]
        resp = self.__exec_cmd(cmd.set_power(update, nxt_state))
        return cmd.payload(resp)

    def get_current(self):
        resp = [self.__exec_cmd(cmd.get_current(m)) for m in range(4)]
        return [cmd.payload(m) for m in resp]

