import system, backend, velmex
import sys, socket, threading, subprocess, time

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

    def wait():
        [r.wait() for r in self.running]

    def stop(self):
        self.stop_ev.set()
        for thr in self.acq_threads:
            thr.join()

class Sorter:
    def __init__(self, fname, n = 4):
        self.inst = subprocess.Popen(
                [system.sorter_bin, fname],
                stdout = sys.stdout, stderr = sys.stderr)

        # wait for server to come up
        time.sleep(1)

        self.socks = []
        for idx in range(n):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
            s.connect(('127.0.0.1', system.sorter_base_port + idx))
            self.socks.append(s)

    def stop(self):
        try:
            self.inst.wait(10.0)
        except subprocess.TimeoutExpired:
            print('Online coincidence sorter did not stop cleanly, killing')
            self.inst.kill()

if __name__ == "__main__":
    stage = velmex.VelmexStage()

    nrings = 80
    step_duration = 600
    step_size = 1.0 # mm between rings
    distance_to_first_ring = 62.2 + 0.5 # mm from front face of system to center of first crystal ring
    stage.move(distance_to_first_ring)

    files = [f'/mnt/acq/{ip}.SGL' for ip in backend_ips]
    #sort = Sorter('/mnt/acq/hello.COIN')
    acq = Acquisition(files)
    acq.wait()

    for i in range(nrings):
        time.sleep(step_duration)
        stage.incr(step_size)

    acq.stop()
    #sort.stop()
