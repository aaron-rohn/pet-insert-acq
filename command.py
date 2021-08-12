class Command():
    RST             = 0

    DAC_WRITE       = 1
    ADC_READ        = 2
    MODULE_ID       = 3

    SET_POWER       = 4
    GET_CURRENT     = 5
    GPIO            = 6
    NOP             = 7

    CMD_EMPTY = 0xF0000000

    @staticmethod
    def cmd_payload(cmd):
        return cmd & 0xFFFFF

    @staticmethod
    def cmd_command(cmd):
        return (cmd >> 20) & 0xF

    @staticmethod
    def cmd_module(cmd):
        return (cmd >> 24) & 0xF

    @staticmethod
    def build_cmd(m, c, p):
        return Command.CMD_EMPTY | ((m & 0xF) << 24) | ((c & 0xF) << 20) | (p & 0xFFFFF)

    @staticmethod
    def rst():
        return Command.CMD_EMPTY

    @staticmethod
    def set_power(update = False, pwr_states = [False]*4):
        bits = pwr_states[0:4] + [update]
        mask = 0
        for s in reversed(bits):
            mask = (mask << 1) | (1 if s else 0)
        return Command.build_cmd(0, Command.SET_POWER, mask)

    @staticmethod
    def get_current(m):
        return Command.build_cmd(m, Command.get_current, 0)

    @staticmethod
    def gpio_rd_backend(offset, mask):
        return Command.build_cmd(0, Command.GPIO, ((offset & 0xFF) << 8) | (mask & 0xFF))

    @staticmethod
    def gpio_rd_rx_err():
        return Command.gpio_rd_backend(0, 0xF)

    @staticmethod
    def gpio_rd_tx_idle():
        return Command.gpio_rd_backend(4, 0xF)

    @staticmethod
    def backend_status(val = 0):
        return Command.build_cmd(0, Command.NOP, val)
