import socket

class Gigex():
    sys_port = 0x5001

    def __init__(self, ip):
        self.ip = ip
        self.sys = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sys.settimeout(1)

    def __enter__(self):
        self.sys.connect((self.ip, Gigex.sys_port))
        return self

    def __exit__(self, *context):
        self.sys.close()

    def spi(self, *data):
        nwords_i = len(data)
        nwords_b = nwords_i.to_bytes(4,'big')

        data = [0] if nwords_i == 0 else data
        data = b''.join([d.to_bytes(4,'big') for d in data])

        cmd = ((0xEE).to_bytes(1,'big') +
               (0x21).to_bytes(1,'big') +
               (0x20).to_bytes(1,'big') +
               (0xFF).to_bytes(1,'big') +
               nwords_b + nwords_b + data)
               #((0).to_bytes(2,'big')) + ((0).to_bytes(2,'big')) + data)

        print(hex(int.from_bytes(cmd, 'big')))

        self.sys.send(cmd)
        resp = self.sys.recv(1024)

        code = resp[0]
        stat = resp[1]

        print("{} {}".format(hex(code), hex(stat)))

        resp = resp[4:]
        resp = [resp[i:i+4] for i in range(0, len(resp), 4)]
        resp = [hex(int.from_bytes(r,'big')) for r in resp]

        return ((code == 0xEE) & (stat == 0), resp)

    def reboot(self):
        cmd = (0xF1000000).to_bytes(4,'big')
        self.sys.sendall(cmd)
        resp = self.recv(1024)
        # returns true on success
        return (resp[0] == 0xF1) & (resp[1] == 0x00)

