import socket
import tkinter as tk

from command import Command

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
        print(cmd_resp_bytes)

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
