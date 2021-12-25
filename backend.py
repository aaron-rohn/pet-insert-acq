import command as cmd
from gigex import Gigex, ignore_network_errors
from frontend import Frontend

class Backend():

    data_port = 5555

    def __getattr__(self, attr):
        return lambda *args, **kwds: [getattr(f, attr)(*args, **kwds) for f in self.frontend]

    def __init__(self, ip):
        self.ip = ip
        self.gx = Gigex(self.ip)
        self.frontend = [Frontend(self, i) for i in range(4)]

    @ignore_network_errors(None)
    def backend_reset(self):
        with self.gx:
            self.gx._spi(cmd.rst())

    @ignore_network_errors(None)
    def flush(self):
        self.gx.flush()

    @ignore_network_errors(None)
    def set_network_led(self, clear = False):
        self.gx.send(cmd.backend_network_set(clear))

    @ignore_network_errors(False)
    def get_status(self):
        c = cmd.backend_status(10)
        return self.gx.send(c) == c

    @ignore_network_errors([True]*4)
    def get_rx_status(self):
        resp = self.gx.send(cmd.gpio_rd_rx_err())
        return cmd.mask_to_bool(cmd.payload(resp) & 0xF)

    @ignore_network_errors([True]*4)
    def get_power(self):
        resp = self.gx.send(cmd.set_power(False, [False]*4))
        return cmd.mask_to_bool(cmd.payload(resp))

    @ignore_network_errors([True]*4)
    def set_power(self, state = [False]*4):
        resp = self.gx.send(cmd.set_power(True, state))
        return cmd.mask_to_bool(cmd.payload(resp))

    @ignore_network_errors([-1]*4)
    def get_current(self):
        resp = [self.gx.send(cmd.get_current(m)) for m in range(4)]
        return [cmd.payload(m) for m in resp]

