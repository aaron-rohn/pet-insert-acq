import socket
import threading
import queue

data_port_num = 5555
control_port_num = 5556

class Sync():
    def __init__(self, ip_addr):
        self.ip_addr = ip_addr

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ip_addr, control_port_num))

    def __del__(self):
        self.sock.close()

    def __transfer_cmd(self, cmd):
        nsent = 0
        cmd_len = len(cmd)

        while nsent < cmd_len:
            just_sent = self.sock.send(cmd)
            cmd = cmd[just_sent:]
            nsent += just_sent

        d = bytearray()

        try:
            while len(d) < cmd_len:
                d += bytearray(self.sock.recv(cmd_len))

        except socket.timeout as e:
            print("{}: timeout reading control socket".format(self.ip_addr))
            d = bytearray(cmd_len)

        return d

    def reset(self):
        rst_cmd = 0xf0000000
        rst_cmd_bytes = rst_cmd.to_bytes(4, byteorder = 'big')
        rst_response = self.__transfer_cmd(rst_cmd_bytes)
        rst_response = int.from_bytes(rst_response, byteorder = 'big')

        if rst_response != rst_cmd:
            print("{}: Invalid reset return value ({})".format(self.ip_addr, hex(rst_response)))
        else:
            print("{}: Reset complete".format(self.ip_addr))

        return rst_response
