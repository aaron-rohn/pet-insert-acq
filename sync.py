import command
from gigex import Gigex

class Sync():
    def __init__(self, ip):
        self.ip = ip
        self.gx = Gigex(self.ip)

    def set_network_led(self, clear = False):
        cmd = command.backend_network_set(clear)
        self.gx.send(cmd)

    def rst(self):
        cmd = command.CMD_EMPTY
        resp = self.gx.send(cmd)
        return resp == (command.CMD_EMPTY | 0x1)

    def get_status(self):
        cmd = command.backend_status(10)
        resp = self.gx.send(cmd)
        return resp == cmd
