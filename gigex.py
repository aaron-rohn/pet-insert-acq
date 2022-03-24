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
                logging.info(f'{repr(e)}\n')
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

    def __enter__(self):
        self.lock.acquire()
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
        self.lock.release()

    def spi(self, *data):
        nwords_i = len(data)
        nwords_b = nwords_i.to_bytes(4,'big')
        data = b''.join([d.to_bytes(4,'big') for d in data])

        cmd_bytes = ((0xEE2120FF).to_bytes(4,'big') +
                nwords_b + nwords_b + data)

        self.sys.send(cmd_bytes)
        code,stat,_,_, *resp = self.sys.recv(1024)

        resp = [resp[i:i+4] for i in range(0, len(resp), 4)]
        resp = [int.from_bytes(r,'big') for r in resp]

        return (code == 0xEE) and (stat == 0), resp

    def flush(self):
        with self:
            try:
                logging.debug(f'{self.ip}: flush connection')
                self.sys.recv(1024*10)
            except TimeoutError:
                pass

    def send(self, cmd_int):
        with self:
            for send_trys in range(5):
                logging.debug(f'{self.ip} send attempt {send_trys+1}: {hex(cmd_int)}')
                status, value = self.spi(cmd_int)

                logging.debug(f'{self.ip}: read backend response')
                status, value = self.spi(0)
                logging.debug(f'{self.ip}: status is {status} and value is {[hex(v) for v in value]}')

                # A reply command type of CMD_RESPONSE indicates that the command was forwarded to the frontend
                if cmd.command(value[0]) != cmd.CMD_RESPONSE:
                    # Backend returns a value directly
                    logging.debug(f'{self.ip}: return backend value {hex(value[0])}\n')
                    return value[0]

                else:
                    # The backend attempted to forward the command to the frontend

                    channel = cmd.module(value[0])
                    response = cmd.payload(value[0])

                    if response == 0:
                        # Backend indicates that the desired module is powered off
                        raise ModuleNotPowered(f'{self.ip}: Channel {channel} is not powered')

                    # Attempt to read back the response from the frontend
                    for recv_trys in range(5):
                        logging.debug(f'{self.ip}: attempt {recv_trys+1} to read back frontend command response on channel {channel}')
                        status, value = self.spi(0)
                        logging.debug(f'{self.ip}: status is {status} and value is {[hex(v) for v in value]}')

                        if cmd.is_command(value[0]) & (cmd.command(value[0]) == cmd.command(cmd_int)):
                            logging.debug(f'{self.ip}: return frontend value {hex(value[0])}\n')
                            return value[0]

        raise GigexError(f'{self.ip}: Did not receive a response to command: {hex(cmd_int)}')

    def reboot(self):
        with self:
            cmd_bytes = (0xF1000000).to_bytes(4,'big')
            self.sys.send(cmd_bytes)
            resp = self.sys.recv(1024)
            # returns true on success
            return resp[0] == 0xF1 and resp[1] == 0x00

