import time
import socket

class Gigex():
    sys_port = 0x5001

    def __init__(self, ip):
        self.ip = ip
        self.sys = None

    def __enter__(self):
        self.sys = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sys.settimeout(1)
        self.sys.connect((self.ip, Gigex.sys_port))
        return self

    def __exit__(self, *context):
        self.sys.close()

    def spi(self, *data):
        nwords_i = len(data)
        nwords_b = nwords_i.to_bytes(4,'big')

        data = [0] if nwords_i == 0 else data
        data = b''.join([d.to_bytes(4,'big') for d in data])

        cmd = ((0xEE2120FF).to_bytes(4,'big') +
               nwords_b + nwords_b + data)

        self.sys.send(cmd)
        code,stat,_,_, *resp = self.sys.recv(1024)

        resp = [resp[i:i+4] for i in range(0, len(resp), 4)]
        resp = [int.from_bytes(r,'big') for r in resp]

        return ((code == 0xEE) & (stat == 0), resp)

    def spi_query(self, cmd):
        print(hex(cmd))
        self.spi(cmd)
        status, value = self.spi(0)
        print(hex(value[0]))
        return value[0] if status else None

    def reboot(self):
        cmd = (0xF1000000).to_bytes(4,'big')
        self.sys.send(cmd)
        resp = self.sys.recv(1024)
        # returns true on success
        return (resp[0] == 0xF1) & (resp[1] == 0x00)

