import command
from gigex import Gigex, ignore_network_errors

class Sync():
    def __init__(self, ip):
        self.ip = ip
        self.gx = Gigex(self.ip)

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

    @ignore_network_errors(-1)
    def set_dac(self, turn_on = False):
        val = 0xFFF if turn_on else 0x0
        cmd = command.dac_write(0, 0, val)
        ret = self.gx.send(cmd)
        return command.payload(ret)

