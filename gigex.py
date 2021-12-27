import time, socket, threading, command, logging

class GigexError(Exception): pass

NetworkErrors = (TimeoutError, ConnectionRefusedError, OSError, GigexError)

def ignore_network_errors(default_return):
    def wrap(unsafe):
        def safe_fun(*args, **kwds):
            try:
                return unsafe(*args, **kwds)
            except NetworkErrors as e:
                logging.error(f'{repr(e)}: {unsafe.__name__}')
                logging.debug('', exc_info = 1)
                return default_return
        return safe_fun
    return wrap

class Gigex():
    sys_port = 0x5001

    def __init__(self, ip):
        self.ip = ip
        self.sys = None
        self.lock = threading.Lock()
        self.local = threading.local()

    def __enter__(self):
        if 'owns' in self.local.__dict__ and self.local.owns:
            return self

        self.lock.acquire()
        self.local.owns = True
        self.sys = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sys.settimeout(0.1)

        try:
            self.sys.connect((self.ip, Gigex.sys_port))
            return self
        except NetworkErrors as e:
            self.__exit__()
            raise e

    def __exit__(self, *context):
        self.sys.close()
        self.local.owns = False
        self.lock.release()

    def spi(self, *data):
        with self:
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

    def flush(self):
        with self:
            try:
                self.sys.recv(1024*10)
            except TimeoutError:
                pass

    def send(self, cmd):
        with self:
            # Try to send the command multiple times
            for _ in range(5):
                self.spi(cmd)

                # Check multiple times for a response
                for _ in range(5):
                    status, value = self.spi(0)

                    # Finish when a valid response is recevied
                    if command.is_command(value[0]):
                        return value[0]

        raise GigexError(f'Did not receive a response to command: {hex(cmd)}')

    def reboot(self):
        with self:
            cmd = (0xF1000000).to_bytes(4,'big')
            self.sys.send(cmd)
            resp = self.sys.recv(1024)
            # returns true on success
            return resp[0] == 0xF1 and resp[1] == 0x00

