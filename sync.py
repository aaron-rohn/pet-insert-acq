import command, threading, queue, logging
from gigex import Gigex, ignore_network_errors
import numpy as np

class Sync():
    def __init__(self, ip):
        self.ip = ip
        self.gx = Gigex(self.ip)
        self.temp_thread = None
        self.temp_queue = queue.Queue()

    @ignore_network_errors(None)
    def set_network_led(self, clear = False):
        cmd = command.backend_network_set(clear)
        self.gx.send(cmd)

    @ignore_network_errors(False)
    def sync_reset(self):
        cmd = command.CMD_EMPTY
        resp = self.gx.send(cmd)
        return resp == (command.CMD_EMPTY | 0x1)

    @ignore_network_errors(False)
    def get_status(self):
        cmd = command.backend_status(10)
        resp = self.gx.send(cmd)
        return resp == cmd

    def toggle_dac(self, turn_on = False):
        return self.set_dac(0xFFF if turn_on else 0x0)

    @ignore_network_errors(-1)
    def set_dac(self, val):
        cmd = command.dac_write(0, 0, val)
        ret = self.gx.send(cmd)
        return command.payload(ret)

    def track_temp_start(self):
        with self.temp_queue.mutex:
            self.temp_queue.queue.clear()

        if self.temp_thread is None:
            self.temp_thread = threading.Thread(target = self.track_temp)
            self.temp_thread.start()

    def track_temp_stop(self):
        if self.temp_thread is not None:
            self.temp_queue.put(None)
            self.temp_thread.join()
        self.temp_thread = None

    def track_temp(self, temp_setpoint = 15.0):
        fullscale = 0xFFF
        kp = fullscale*0.05
        ki = fullscale*0.01
        kd = fullscale*0.01

        e_sum = 0
        e_last = 0

        # start the control loop with max cooling
        u = fullscale
        self.set_dac(u)

        while True:
            temps = self.temp_queue.get()
            if temps is None: break

            temps = np.array(temps).flat
            temps = temps[temps != -1].tolist()

            try:
                avg = sum(temps) / len(temps)
                logging.info(f'measured average tmp {avg} at set value {hex(u)}')
            except ZeroDivisionError:
                # no temp was measured
                logging.info(f'no temperatures were measured')
                continue

            e = avg - temp_setpoint

            if u == fullscale and e > -1:
                logging.info(f'skipping adjustment since set value is at full scale')
                e_sum = 0
                continue

            p = kp * e

            e_sum += e
            i = ki * e_sum 

            d = kd * (e - e_last)
            e_last = e

            logging.info(f'p: {p}, i: {i}, d: {d}')

            u += (p + i - d)
            u = max(0, min(u, fullscale))

            logging.info(f'set u to {u}')

            self.set_dac(u)

        self.set_dac(0)
