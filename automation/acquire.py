import system, backend, velmex
import sys, socket, threading, subprocess, time, logging
from gigex import cmd_port
import command

backend_ips = ['192.168.1.101', '192.168.1.102', '192.168.1.103', '192.168.1.104']

class Acquisition:
    def __init__(self, sinks):
        # sinks can be a list of:
        # filenames -> singles acq
        # sockets -> coincidence acq

        self.stop_ev = threading.Event()
        self.acq_threads = []
        self.running = []

        for ip, sink in zip(backend_ips, sinks):
            r = threading.Event()
            self.running.append(r)

            thr = threading.Thread(
                    target = backend.acquire,
                    args = [ip, self.stop_ev, sink, r])
            self.acq_threads.append(thr)
            thr.start()

    def wait(self):
        [r.wait() for r in self.running]
        print('Acquisition is running')

    def stop(self):
        self.stop_ev.set()
        for thr in self.acq_threads:
            thr.join()

    @staticmethod
    def reset():
        c = socket.create_connection(('127.0.0.1', cmd_port))
        cmd = command.CMD_EMPTY
        c.send(cmd.to_bytes(4, 'big'))
        resp = c.recv(4)
        c.close()

        resp = int.from_bytes(resp, 'big')
        if resp != (command.CMD_EMPTY | 0x1):
            logging.error(f'Got response {hex(resp)} when performing reset')
        else:
            logging.info('Time tags reset')

        return resp

class Sorter:
    def __init__(self, fname, n = 4):
        self.inst = subprocess.Popen(
                [system.sorter_bin, fname],
                stdout = sys.stdout, stderr = sys.stderr)

        # wait for server to come up
        time.sleep(1)
        self.socks = [socket.create_connection(('127.0.0.1', system.sorter_base_port + i)) for i in range(n)]
        print('Connected to online coincidence sorter')

    def stop(self):
        try:
            self.inst.wait(10.0)
        except subprocess.TimeoutExpired:
            print('Online coincidence sorter did not stop cleanly, killing')
            self.inst.kill()

if __name__ == "__main__":

    logging.basicConfig(level = logging.INFO)

    nrings = 80
    step_duration = 600
    step_size = 1.0 # mm between rings
    distance_to_first_ring = 62.2 + 0.5 # mm from front face of system to center of first crystal ring

    #stage = velmex.VelmexStage()
    #stage.move(distance_to_first_ring)

    #files = [f'/mnt/acq/{ip}.SGL' for ip in backend_ips]
    sort = Sorter('/mnt/acq/hello.COIN')
    acq = Acquisition(sort.socks)
    acq.wait()
    acq.reset()

    for i in range(5):
        time.sleep(60)
        print(i)

    #for i in range(nrings):
    #    time.sleep(step_duration)
    #    stage.incr(step_size)

    acq.stop()
    sort.stop()
