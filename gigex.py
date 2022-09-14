import time, socket, threading, logging, queue
import command as cmd

class ModuleNotPowered(Exception): pass

NetworkErrors = (TimeoutError, ConnectionRefusedError, OSError)

sys_port = 0x5001
cmd_port = 5556

def ignore_network_errors(default_return):
    def wrap(unsafe):
        def safe_fun(*args, **kwds):
            try:
                return unsafe(*args, **kwds)
            except ModuleNotPowered as e:
                logging.debug(f'{repr(e)}')
            except NetworkErrors as e:
                logging.debug('', exc_info = 1)
            except Exception as e:
                logging.warn('Caught unknown exception', exc_info = 1)
            return default_return

        return safe_fun
    return wrap

def flush(s):
    timeout = s.gettimeout()
    s.settimeout(0)
    while True:
        try:
            s.recv(1024)
        except BlockingIOError:
            s.settimeout(timeout)
            return

def connect(s, ip, port, timeout):
    if isinstance(s, socket.socket):
        s.close()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip,port))
    except Exception as e:
        logging.info(f'{ip}: Failed to connect to port {port}, {e}')
    return s

def handle_single(s, cmd_int):
    cmd_bytes = cmd_int.to_bytes(4,'big')
    s.send(cmd_bytes)
    resp_bytes = s.recv(4)
    resp_int = int.from_bytes(resp_bytes, 'big')

    if cmd.command(resp_int) != cmd.CMD_RESPONSE:
        return resp_int

    elif cmd.payload(resp_int) == 0:
        chn = cmd.module(resp_int)
        ex = ModuleNotPowered(f'Channel {chn} is not powered')
        return ex

    else:
        resp_bytes = s.recv(4)
        resp_int = int.from_bytes(resp_bytes, 'big')
        return resp_int

def handle(s, cmd_int):
    for _ in range(5):
        flush(s)
        try:
            return s, handle_single(s, cmd_int)
        except TimeoutError:
            pass
        except Exception as e:
            s = connect(s, ip, cmd_port, timeout)
            return s, e

    return s, TimeoutError(f'Timeout sending command {hex(cmd_int)}')

def run(ip, queue_in, queue_out):
    timeout = 0.1
    s = connect(None, ip, cmd_port, timeout)
    while True:
        cmd_int = queue_in.get()

        if cmd_int is None:
            break

        s, response = handle(s, cmd_int)
        queue_out.put(response)

    s.close()

class Gigex():
    def __init__(self, ip):
        self.ip = ip
        self.lock = threading.Lock()
        self.queue_in = queue.Queue()
        self.queue_out = queue.Queue()

    def start(self):
        self.thr = threading.Thread(target = run,
                daemon = True, args = [self.ip, self.queue_in, self.queue_out])
        self.thr.start()

    def stop(self):
        self.queue_in.put(None)
        self.thr.join()

    def send(self, val):
        with self.lock:
            self.queue_in.put(val)
            response = self.queue_out.get()

        if isinstance(response, Exception):
            raise response

        return response

    @ignore_network_errors((False,[]))
    def spi(self, *data):
        nwords_i = len(data)
        nwords_b = nwords_i.to_bytes(4,'big')
        data = b''.join([d.to_bytes(4,'big') for d in data])
        cmd_bytes = ((0xEE2120FF).to_bytes(4,'big') +
                nwords_b + nwords_b + data)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.ip, sys_port))
        s.send(cmd_bytes)
        code,stat,_,_, *resp = self.sys.recv(1024)
        s.close()

        resp = [resp[i:i+4] for i in range(0, len(resp), 4)]
        resp = [int.from_bytes(r,'big') for r in resp]
        return (code == 0xEE) and (stat == 0), resp

    @ignore_network_errors(False)
    def reboot(self):
        cmd_bytes = (0xF1000000).to_bytes(4,'big')

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.ip, sys_port))
        s.send(cmd_bytes)
        resp = self.sys.recv(1024)
        s.close()

        good = (resp[0] == 0xF1 and resp[1] == 0x00)
        logging.info(f'Reboot result {self.ip}: {good}')
        return good

