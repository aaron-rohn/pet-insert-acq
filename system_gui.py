import socket

import tkinter as tk

from time import sleep
from tkinter import messagebox
from tkinter.ttk import Separator, Sizegrip
from tkinter.scrolledtext import ScrolledText

def to_mask(num):
    return format(num, '#06b')

class Command():
    RST             = 0

    DAC_WRITE       = 1
    ADC_READ        = 2
    MODULE_ID       = 3

    SET_POWER       = 4
    GET_CURRENT     = 5
    GPIO            = 6
    NOP             = 7
    UART            = 8

    CMD_EMPTY = 0xF0000000

    @staticmethod
    def cmd_payload(cmd):
        return cmd & 0xFFFFF

    @staticmethod
    def cmd_command(cmd):
        return (cmd >> 20) & 0xF

    @staticmethod
    def cmd_module(cmd):
        return (cmd >> 24) & 0xF

    @staticmethod
    def build_cmd(m, c, p):
        return Command.CMD_EMPTY | ((m & 0xF) << 24) | ((c & 0xF) << 20) | (p & 0xFFFFF)

    @staticmethod
    def rst():
        return Command.CMD_EMPTY

    @staticmethod
    def set_power(update = False, pwr_states = [False]*4):
        bits = pwr_states[0:4] + [update]
        mask = 0
        for s in reversed(bits):
            mask = (mask << 1) | (1 if s else 0)
        return Command.build_cmd(0, Command.SET_POWER, mask)

    @staticmethod
    def get_current(m):
        return Command.build_cmd(m, Command.get_current, 0)

    @staticmethod
    def gpio_rd_backend(offset, mask):
        return Command.build_cmd(0, Command.GPIO, ((offset & 0xFF) << 8) | (mask & 0xFF))

    @staticmethod
    def gpio_rd_rx_err():
        return Command.gpio_rd_backend(0, 0xF)

    @staticmethod
    def gpio_rd_tx_idle():
        return Command.gpio_rd_backend(4, 0xF)

    @staticmethod
    def backend_status(val = 0):
        return Command.build_cmd(0, Command.NOP, val)

    @staticmethod
    def uart():
        return Command.build_cmd(0, Command.UART, 0)

class Backend():
    data_port = 5555
    ctrl_port = 5556

    @staticmethod
    def __cmd_to_bytes(cmd_int):
        return cmd_int.to_bytes(4, byteorder = 'big')

    @staticmethod
    def __cmd_from_bytes(cmd_bytes):
        return int.from_bytes(cmd_bytes, byteorder = 'big')

    def __init__(self, parent_frame, label, ip):
        self.ip = ip

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

    def __transfer_cmd(self, cmd):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)

        try:
            s.connect((self.ip, self.ctrl_port))
            s.send(cmd)
            d = s.recv(1024)

        except socket.timeout as e:
            print("({}) Error connecting to socket: {} ".format(self.ip, e))
            d = None

        s.close()
        return d

    def __exec_cmd(self, cmd, *args):
        cmd_int = cmd(*args)
        cmd_bytes = Backend.__cmd_to_bytes(cmd_int)
        cmd_resp_bytes = self.__transfer_cmd(cmd_bytes)
        cmd_resp_int = Backend.__cmd_from_bytes(cmd_resp_bytes)
        return cmd_resp_int

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
        pow_state = [m.get() for m in self.m_pow_var]
        cmd_resp = self.__exec_cmd(Command.set_power, update, pow_state)
        return Command.cmd_payload(cmd_resp) & 0xF

    def uart(self):
        cmd_resp = self.__exec_cmd(Command.uart)
        return Command.cmd_payload(cmd_resp)

class App(tk.Frame):
    def __init__(self):
        self.root = tk.Tk()
        super().__init__(self.root)
        self.draw()

    def draw(self):
        self.backend_frame = tk.Frame(self.root)
        self.backend_frame.pack()

        self.backend_label = tk.Label(self.backend_frame, text = "Backend")
        self.backend_label.pack(fill = "both", expand = True, padx = 10)

        backend_ips = ['192.168.1.101']
        backend_lab = ['Data']
        
        args = zip([self.backend_frame]*len(backend_ips), backend_lab, backend_ips)
        self.backend = [Backend(*a) for a in args]

        # Refresh backend status
        refresh_callback = lambda: [b.set_status() for b in self.backend]
        self.backend_refresh = tk.Button(self.backend_frame, text = "Refresh", command = refresh_callback)
        self.backend_refresh.pack(fill = "both", expand = True, padx = 10, pady = 10)

        def callback_gen(func, *args):
            return lambda: self.print([to_mask(getattr(b, func)(*args)) for b in self.backend])

        rx_status_callback = callback_gen('get_rx_status')
        tx_status_callback = callback_gen('get_tx_status')
        power_rd_callback  = callback_gen('get_set_frontend_power', False)
        power_wr_callback  = callback_gen('get_set_frontend_power', True)
        uart_callback      = lambda: self.print(self.backend[0].uart().to_bytes(5,'big'))

        self.backend_rx_status = tk.Button(self.backend_frame, text = "Update RX status", command = rx_status_callback)
        self.backend_tx_status = tk.Button(self.backend_frame, text = "Update TX status", command = tx_status_callback)
        self.power_rd_callback = tk.Button(self.backend_frame, text = "Read power state", command = power_rd_callback)
        self.power_wr_callback = tk.Button(self.backend_frame, text = "Set power state", command = power_wr_callback)
        self.uart_callback     = tk.Button(self.backend_frame, text = "Uart heartbeat", command = uart_callback)

        self.backend_rx_status.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.backend_tx_status.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.power_rd_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.power_wr_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.uart_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)

        Separator(self.root, orient = "horizontal").pack(fill = tk.X, expand = True, padx = 10, pady = 10)

        self.status_text = ScrolledText(master = self.root, width = 60, height = 10, takefocus = False)
        self.status_text.pack(fill = "both", expand = True, padx = 10, pady = 10)

    def print(self, txt):
        self.status_text.insert(tk.END, str(txt) + "\n")
        self.status_text.yview(tk.END)

app = App()
app.mainloop()
