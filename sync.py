import command, threading, queue, logging, socket
from gigex import Gigex, ignore_network_errors, cmd_port
import numpy as np
from labjack import ljm
from simple_pid import PID

def set_air_ljm(value):
    fullscale = 5.0
    setpoint = fullscale*value

    # Open first found LabJack
    handle = ljm.openS("ANY", "ANY", "ANY")

    # addresses, datatypes, operation, number of values, values
    results = ljm.eAddresses(handle, 1,
            [1000], [ljm.constants.FLOAT32], [ljm.constants.WRITE], [1], [setpoint])

    ljm.close(handle)
    return results[0]

class Sync():
    def __init__(self, ip):
        self.ip = ip
        self.gx = Gigex(self.ip)
        self.temp_thread = None
        self.temp_queue = queue.Queue()

    def __enter__(self):
        self.gx.start()
        self.set_network_led(clear = False)
        self.listener = socket.create_server(('127.0.0.1', cmd_port))
        self.listener_thread = threading.Thread(target = self.remote_listener)

    def __exit__(self, *context):
        self.listener.close()
        self.listener.shutdown()
        self.listener_thread.join()
        self.set_network_led(clear = True)
        self.gx.stop()

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
        return set_air_ljm(1.0 if turn_on else 0.0)

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

    def track_temp(self, temp_setpoint = 18.0):
        pid = PID(-0.2, -0.01, -0.01,
                setpoint = temp_setpoint,
                sample_time = 10,
                output_limits = (0.2, 0.8))

        set_air_ljm(0.5)

        while True:
            temps = self.temp_queue.get()
            if temps is None: break

            temps = np.array(temps).flat
            temps = temps[temps > 0].tolist()

            try:
                avg = sum(temps) / len(temps)
            except ZeroDivisionError:
                # no temp was measured
                logging.debug(f'no temperatures were measured')
                continue

            u = pid(avg)
            logging.debug(f'measured average tmp {round(avg,3)}, u = {round(u,3)}')
            set_air_ljm(u)

        set_air_ljm(0.0)

    def remote_listener(self):
        while True:
            try:
                c, addr = self.listener.accept()
            except:
                logging.exception('Exit from remote listener thread')
                return

            cmd = c.recv(1024)
            cmd = int.from_bytes(cmd, 'big')
            ret = self.gx.send(cmd)
            c.sendall(ret.to_bytes(4, 'big'))
            c.close()
