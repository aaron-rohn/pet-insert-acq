RST             = 0
DAC_WRITE       = 1
ADC_READ        = 2
MODULE_ID       = 3
SET_POWER       = 4
GET_CURRENT     = 5
GPIO            = 6
NOP             = 7

CMD_EMPTY = 0xF0000000

def payload(cmd_int):
    return cmd_int & 0xFFFFF

def module(cmd_int):
    return (cmd_int >> 24) & 0xF

def build(m, c, p):
    return CMD_EMPTY | ((m & 0xF) << 24) | ((c & 0xF) << 20) | (p & 0xFFFFF)

def rst():
    return CMD_EMPTY

def set_power(update = False, pwr_states = [False]*4):
    bits = pwr_states[0:4] + [update]
    mask = 0
    for s in reversed(bits):
        mask = (mask << 1) | (1 if s else 0)
    return build(0, SET_POWER, mask)

def get_current(m):
    return build(m, GET_CURRENT, 0)

def gpio_rd_backend(offset, mask):
    return build(0, GPIO, ((offset & 0xFF) << 8) | (mask & 0xFF))

def gpio_rd_rx_err():
    return gpio_rd_backend(0, 0xF)

def gpio_rd_tx_idle():
    return gpio_rd_backend(4, 0xF)

def backend_status(val = 0):
    return build(0, NOP, val)

def dac_write(module, channel, value):
    channel &= 0xF
    value &= 0xFFF
    return build(module, DAC_WRITE, (0x3 << 16) | (channel << 12) | value)

def adc_read(module, channel):
    channel &= 0xF
    return build(module, ADC_READ, (channel << 16))

def module_id(m):
    return build(m, MODULE_ID, 0)
