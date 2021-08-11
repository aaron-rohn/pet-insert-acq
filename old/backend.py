import socket
import threading
import queue

from frontend import Frontend

control_port_num = 5556
data_port_num = 5555

class Backend():

    @staticmethod
    def run_acq(sock, fname, finished):
        with open(fname, 'wb') as f:
            try:
                while not finished.is_set():
                    f.write(bytes(sock.recv(4096)))

            except socket.timeout as e:
                print("{}: Timeout reading data socket".format(sock.getpeername()))

    @staticmethod
    def run_monitor(finished, queue_in, queue_out):
        """
        This method just provides an isolated context to make
        calls to the control socket. The control socket should
        not be read/written to from any other thread.
        """
        while not finished.is_set():
            cmd = queue_in.get()
            queue_out.put(cmd())

    def __init__(self, ip_addr, nmodules, acq_finished):
        self.ip_addr = ip_addr
        self.nmodules = nmodules 

        # no timeout on the data socket
        self.data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_sock.connect((ip_addr, data_port_num))

        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_sock.settimeout(10)
        self.control_sock.connect((ip_addr, control_port_num))

        self.modules = [Frontend(self.__transfer_cmd, idx) for idx in range(nmodules)]

        self.acq_thread = None
        self.acq_finished = acq_finished

        self.monitor_thread = None
        self.monitor_finished = threading.Event()
        self.monitor_lock = threading.Lock()
        self.monitor_queue_in = queue.Queue()
        self.monitor_queue_out = queue.Queue()

    def __del__(self):
        self.data_sock.close()
        self.control_sock.close()

    def __transfer_cmd(self, cmd):
        nsent = 0
        cmd_len = len(cmd)

        while nsent < cmd_len:
            just_sent = self.control_sock.send(cmd)
            cmd = cmd[just_sent:]
            nsent += just_sent

        d = bytearray()

        try:
            while len(d) < cmd_len:
                d += bytearray(self.control_sock.recv(cmd_len))

            d = d[:cmd_len]

        except socket.timeout as e:
            print("{}: timeout reading control socket".format(self.ip_addr))
            d = None

        return d

    # Private methods for frontend control

    def __set_dac(self, is_bias, mod_blk_val_lst):
        return [self.modules[m].set_dac(is_bias, b, v) for m,b,v in mod_blk_val_lst]

    def __get_temp(self, mod_blk_lst):
        ret = [self.modules[m].get_temp(b) for m,b in mod_blk_lst]
        return [Frontend.adc_to_temp(a) for _,a in ret]

    def __get_power(self):
        return [m.get_power() for m in self.modules]

    def __set_power(self, mask):
        cmd = 0xf0400000 | mask << 16
        cmd_bytes = cmd.to_bytes(4, byteorder = 'big')
        ret = self.__transfer_cmd(cmd_bytes)
        ret = int.from_bytes(ret, byteorder = 'big') if ret else None

        if ret != cmd:
            ret_str = hex(ret) if ret else str(None)
            print("{}: Invalid response when setting power ({})".format(self.ip_addr, ret_str))

        return ret

    # Public methods

    def set_dac(self, *args, **kwargs):
        if self.monitor_thread is not None:
            with self.monitor_lock:
                self.monitor_queue_in.put(lambda: self.__set_dac(*args, **kwargs))
                ret = self.monitor_queue_out.get()
        else:
            ret = []

        return ret

    def get_temp(self, *args, **kwargs):
        if self.monitor_thread is not None:
            with self.monitor_lock:
                self.monitor_queue_in.put(lambda: self.__get_temp(*args, **kwargs))
                ret = self.monitor_queue_out.get()
        else:
            ret = []

        return ret

    def set_power(self, *args, **kwargs):
        if self.monitor_thread is not None:
            with self.monitor_lock:
                self.monitor_queue_in.put(lambda: self.__set_power(*args, **kwargs))
                ret = self.monitor_queue_out.get()
        else:
            ret = []

        return ret

    def get_power(self):
        if self.monitor_thread is not None:
            with self.monitor_lock:
                self.monitor_queue_in.put(lambda: self.__get_power())
                ret = self.monitor_queue_out.get()
        else:
            ret = []

        return ret

    def power_all_modules(self, power_on = True):
        mask = 0

        if power_on:
            for bit in range(self.nmodules):
                mask |= (1 << bit)

            mask &= 0xF

        mask_str = "{0:b}".format(mask).zfill(4)
        print("{}: Setting power to {}".format(self.ip_addr, mask_str))

        return self.set_power(mask)

    def launch_monitor(self):
        if self.monitor_thread is None:
            self.monitor_finished.clear()

            args = (self.monitor_finished, 
                    self.monitor_queue_in, 
                    self.monitor_queue_out)

            self.monitor_thread = threading.Thread(target = Backend.run_monitor, args = args)
            self.monitor_thread.start()

    def kill_monitor(self):
        if self.monitor_thread is not None:
            with self.monitor_lock:
                self.monitor_finished.set()
                self.monitor_queue_in.put(lambda: None)
                self.monitor_queue_out.get()
                self.monitor_thread.join()

            self.monitor_thread = None

    def launch_acq(self, fname):
        if self.acq_thread is None:
            args = (self.data_sock, fname, self.acq_finished)
            self.acq_thread = threading.Thread(target = Backend.run_acq, args = args)
            self.acq_thread.start()

    def kill_acq(self):
        if self.acq_thread is not None:
            self.acq_thread.join()
            self.acq_thread = None
