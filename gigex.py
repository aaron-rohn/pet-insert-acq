import time, socket, threading, logging
import command as cmd

class GigexError(Exception): pass
class ModuleNotPowered(Exception): pass

NetworkErrors = (TimeoutError, ConnectionRefusedError, OSError, GigexError)

def ignore_network_errors(default_return):
    def wrap(unsafe):
        def safe_fun(*args, **kwds):
            try:
                return unsafe(*args, **kwds)

            except ModuleNotPowered as e:
                logging.debug(f'{repr(e)}')
                return default_return

            except NetworkErrors as e:
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
        self.timeout = 0.1

    def __enter__(self):
        self.lock.acquire()
        self.sys = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sys.settimeout(self.timeout)

        try:
            self.sys.connect((self.ip, Gigex.sys_port))
            return self
        except NetworkErrors as e:
            self.__exit__()
            raise e

    def __exit__(self, *context):
        self.sys.close()
        self.lock.release()

    def spi(self, *data):
        nwords_i = len(data)
        nwords_b = nwords_i.to_bytes(4,'big')
        data = b''.join([d.to_bytes(4,'big') for d in data])

        # (35->0/17.5->1/8.75->2) MHz SPI access
        # 32 bit word length
        # release chip select
        cmd_bytes = ((0xEE2120FF).to_bytes(4,'big') +
                nwords_b + nwords_b + data)

        self.sys.send(cmd_bytes)
        code,stat,_,_, *resp = self.sys.recv(1024)

        resp = [resp[i:i+4] for i in range(0, len(resp), 4)]
        resp = [int.from_bytes(r,'big') for r in resp]

        return (code == 0xEE) and (stat == 0), resp

    def _flush(self):
        logging.debug(f'{self.ip}: flush connection')
        self.sys.settimeout(0.0)
        try:
            self.sys.recv(1024)
        except:
            pass
        self.sys.settimeout(self.timeout)

    def _recv(self, cmd_type = None, ntrys = 5, wait = 100e-6):
        for i in range(ntrys):
            time.sleep(wait)
            status, value = self.spi(0)

            if not status:
                raise GigexError(f'{self.ip}: Error reading SPI')

            cmd_general  = cmd_type is None and cmd.is_command(value[0])
            cmd_specific = cmd.command(value[0]) == cmd_type

            if cmd_specific or cmd_general:
                logging.debug(f'{self.ip}: Read response {hex(value[0])} on try {i+1}')
                return value[0]

        raise GigexError(f'{self.ip}: Failed to receive a nonzero value')

    def _query(self, cmd_int):
        logging.debug(f'{self.ip}: Send command {hex(cmd_int)}')
        self.spi(cmd_int)
        value = self._recv(wait = 10e-6)

        if cmd.command(value) != cmd.CMD_RESPONSE:
            return value

        if cmd.payload(value) == 0:
            raise ModuleNotPowered(f'{self.ip}: Channel {cmd.module(value)} is not powered')

        cmd_type = cmd.command(cmd_int)
        return self._recv(cmd_type = cmd_type, wait = 10e-3)

    def send(self, cmd_int, nsend_trys = 5):
        with self:
            self._flush()
            for send_trys in range(nsend_trys):
                logging.debug(f'{self.ip}: Send attempt {send_trys+1}')
                try:
                    return self._query(cmd_int)
                except GigexError as ge:
                    logging.debug(repr(ge))

            self.spi(1)
            self._flush()
            raise GigexError(f'{self.ip}: Failed to receive response after {nsend_trys} trys')

    def reboot(self):
        with self:
            cmd_bytes = (0xF1000000).to_bytes(4,'big')
            self.sys.send(cmd_bytes)
            #resp = self.sys.recv(1024)
            # returns true on success
            #return resp[0] == 0xF1 and resp[1] == 0x00

