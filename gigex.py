import time, socket, threading, logging, queue
import command as cmd

class ModuleNotPowered(Exception): pass

NetworkErrors = (TimeoutError, ConnectionRefusedError, OSError)

sys_port = 0x5001
cmd_port = 5556
info_port = 5557

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

def connect(s, ip, port, timeout = None):
    if isinstance(s, socket.socket):
        s.close()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip,port))
    except Exception as e:
        logging.debug(f'{ip}: Failed to connect to port {port}, {e}')
    return s

def handle(s, cmd_int):
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

def run(ip, queue_in, queue_out):
    timeout = 0.1
    s = connect(None, ip, cmd_port, timeout)
    while True:
        cmd_int = queue_in.get()

        if cmd_int is None:
            break

        for _ in range(5):
            try:
                flush(s)
                response = handle(s, cmd_int)
            except TimeoutError as e:
                response = e
                continue
            except Exception as e:
                response = e
                s = connect(s, ip, cmd_port, timeout)
            break

        queue_out.put(response)

    s.close()

class Gigex():
    def __init__(self, ip):
        self.ip = ip
        self.lock = threading.Lock()
        self.queue_in = queue.Queue()
        self.queue_out = queue.Queue()

        self.info_stop = threading.Event()
        self.info_lock = threading.Lock()
        self.info_queue = queue.Queue()

    def start(self):
        self.thr = threading.Thread(target = run,
                args = [self.ip, self.queue_in, self.queue_out])
        self.thr.start()

        self.info_thr = threading.Thread(target = self.info)
        self.info_thr.start()

    def stop(self):
        self.queue_in.put(None)
        self.thr.join()

        self.info_stop.set()
        with self.info_lock:
            try:
                self.info_sock.shutdown(socket.SHUT_RD)
            except: pass
        self.info_thr.join()

    def send(self, val):
        with self.lock:
            self.queue_in.put(val)
            response = self.queue_out.get()

        if isinstance(response, Exception):
            raise response

        return response

    def info(self):
        with self.info_lock:
            self.info_sock = connect(None, self.ip, info_port)

        while not self.info_stop.wait(1):
            try:
                val = self.info_sock.recv(4)
                if len(val) == 0: break
                self.info_queue.put((self.ip, val))
            except Exception as e:
                with self.info_lock:
                   self.info_sock = connect(self.info_sock,
                                            self.ip, info_port)

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

