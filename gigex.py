import time
import socket
import threading
import command

class Gigex():
    sys_port = 0x5001

    def __init__(self, ip):
        self.ip = ip
        self.sys = None
        self.lock = threading.Lock()

    def __enter__(self):
        self.lock.acquire()
        self.sys = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sys.settimeout(0.1)
        self.sys.connect((self.ip, Gigex.sys_port))
        return self

    def __exit__(self, *context):
        self.sys.close()
        self.lock.release()

    def flush(self):
        #timeout = self.sys.gettimeout()
        #self.sys.settimeout(1)
        try:
            self.sys.recv(1024*10)
        except socket.timeout:
            pass
        #self.sys.settimeout(timeout)

    def spi(self, *data):
        nwords_i = len(data)
        nwords_b = nwords_i.to_bytes(4,'big')
        data = b''.join([d.to_bytes(4,'big') for d in data])

        cmd = ((0xEE2120FF).to_bytes(4,'big') +
               nwords_b + nwords_b + data)

        self.sys.send(cmd)
        code,stat,_,_, *resp = self.sys.recv(1024)

        resp = [resp[i:i+4] for i in range(0, len(resp), 4)]
        resp = [int.from_bytes(r,'big') for r in resp]

        return (code == 0xEE) and (stat == 0), resp

    def spi_query(self, cmd):

        class ExitLoop(Exception): pass

        try:
            # Try to send the command multiple times
            for _ in range(5):
                self.spi(cmd)

                # Check multiple times for a response
                for _ in range(5):
                    status, value = self.spi(0)

                    # Finish when a valid response is recevied
                    if command.is_command(value[0]):
                        raise ExitLoop

            status = False
            #print("sending command failed")

        except ExitLoop:
            pass

        return value[0] if status else None

    def reboot(self):
        cmd = (0xF1000000).to_bytes(4,'big')
        self.sys.send(cmd)
        resp = self.sys.recv(1024)
        # returns true on success
        return resp[0] == 0xF1 and resp[1] == 0x00

