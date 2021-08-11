import os
import time
import threading
import signal
import csv
import numpy

from datetime import datetime
from backend import Backend
from sync import Sync

MAX_BIAS = 29.0

class System():

    def __init__(self, ip_addr_sync, ip_addr_list, nmodules, folder = '.', temp_fname = None):

        self.folder = folder

        self.temp_thread = None
        self.temp_ev = threading.Event()
        self.acq_ev  = threading.Event()

        self.temp_handle = None
        self.temp_csv_writer = None
        self.fieldnames = None

        self.sync = Sync(ip_addr_sync)
        self.backend = [Backend(ip,n,self.acq_ev) for ip,n in zip(ip_addr_list,nmodules)]

        if temp_fname is not None:
            self.fieldnames = ['time'] + [str(i) for i in range(sum(nmodules)*8)]
            self.temp_handle = open(temp_fname, mode = 'w')
            self.temp_csv_writer = csv.DictWriter(self.temp_handle, fieldnames = self.fieldnames)
            self.temp_csv_writer.writeheader()

    def __enter__(self):
        #self.start_acq()
        #self.start_monitor()
        self.set_all_power(False)
        time.sleep(5)

        self.reset()
        time.sleep(1)

        #self.temp_thread = threading.Thread(target = self.get_temp_at_interval)
        #self.temp_thread.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_acq()
        self.temp_ev.set()

        if self.temp_thread is not None:
            self.temp_thread.join()

        if self.temp_handle is not None:
            self.temp_handle.close()

        self.set_all_dac(False, 0.1)
        self.set_all_dac(True, 0)
        self.set_all_power(False)

        self.stop_monitor()

    def reset(self):
        self.sync.reset()

    def start_acq(self, ext = '.dat'):
        self.acq_ev.clear()
        [b.launch_acq(os.path.join(self.folder, b.ip_addr + ext)) for b in self.backend]

    def stop_acq(self):
        self.acq_ev.set()
        [b.kill_acq() for b in self.backend]

    def start_monitor(self):
        [b.launch_monitor() for b in self.backend]

    def stop_monitor(self):
        [b.kill_monitor() for b in self.backend]

    def validate_dac(self, dac_return):
        backend_idx = 0
        for backend_return in dac_return:
            for cmd_in, cmd_out in backend_return:

                a = int.from_bytes(cmd_in,  byteorder = 'big') & 0xFFF
                b = int.from_bytes(cmd_out, byteorder = 'big') & 0xFFF if cmd_out else None

                if a != b :
                    backend_ip = self.backend[backend_idx].ip_addr
                    b_str = hex(b) if b is not None else str(None)
                    print("{}: invalid dac value ({}, {})".format(backend_ip, hex(a), b_str))

            backend_idx += 1

    def set_all_dac(self, is_bias, value):
        value = value if value < MAX_BIAS else MAX_BIAS

        ret = []

        for b in self.backend:
            mod_blk_val_lst = []

            for m in range(b.nmodules):
                mod_blk_val_lst += zip([m]*4, range(4), [value]*4)

            ret.append(b.set_dac(is_bias, mod_blk_val_lst))
        
        self.validate_dac(ret)
        return ret

    def get_all_temp(self):
        ret = []

        for b in self.backend:
            mod_blk_lst = []

            for m in range(len(b.modules)):
                mod_blk_lst += zip([m]*8, range(8))

            ret.append(b.get_temp(mod_blk_lst))

        return ret

    def get_all_power(self):
        return [b.get_power() for b in self.backend]

    def set_all_power(self, power_on = True):
        ret = [b.power_all_modules(power_on) for b in self.backend]
        return ret

    def get_temp_at_interval(self):

        self.temp_ev.clear()
        ev = threading.Event()
        timer_func = lambda: ev.set()

        def exit_func():
            self.temp_ev.wait()
            ev.set()

        t = threading.Thread(target = exit_func)
        t.start()

        while not self.temp_ev.is_set():

            temp_vals = self.get_all_temp()
            power_vals = self.get_all_power()

            temp_vals = [t for sl in temp_vals for t in sl]
            temp_vals_rounded = [round(v) if v else None for v in temp_vals]

            print("max temp: {}".format(max(temp_vals_rounded)))
            print(power_vals)

            if self.temp_handle is not None:
                try:
                    temp_vals = [datetime.now()] + temp_vals
                    newrow = dict(zip(self.fieldnames, temp_vals))
                    self.temp_csv_writer.writerow(newrow)
                    self.temp_handle.flush()
                except Exception as e:
                    print(str(e))
                    self.temp_handle.close()
                    self.temp_handle = None

            timer = threading.Timer(10, timer_func)
            timer.start()

            ev.wait()
            ev.clear()

            if timer.is_alive(): timer.cancel()

if __name__ == "__main__":

    """
    ip_list = [
            '192.168.1.101',
            '192.168.1.102',
            '192.168.2.103',
            '192.168.2.104',
            ]

    nmod_list = [4,4,4,4]
    """
    ip_list = ['192.168.1.101']
    nmod_list = [2]

    with System('192.168.1.100', ip_list, nmod_list) as sys:
        #sys.set_all_dac(False, 0.05)
        #sys.set_all_dac(True, 29)

        print(sys.get_all_power())

        try:
            time.sleep(5)
        except KeyboardInterrupt:
            pass
