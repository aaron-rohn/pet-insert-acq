def mask_to_bool(val, n = 4):
    return [bool(val & (1 << i)) for i in range(n)]

def bool_to_mask(bits):
    value = 0
    for i,v in enumerate(bits):
        value |= (int(v) << i)
    return value

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

# Backend commands

def gpio_backend(write = 0, bank = 1, offset = 0, mask = 0, value = 0):
    """ bank == 0 is the r/w (output) bank, 1 is the input bank

    For writes the operation is:
        val = bank0
        val &= ~(mask << offset)
        val |= (mask & value) << offset
        bank0 = val

    For reads and writes, the return is:
        (bank_i >> offset) & mask

    """
    return build(0, GPIO, (((write  & 0x03) << 18) |
                           ((bank   & 0x03) << 16) | 
                           ((offset & 0xFF) <<  8) |
                           ((mask   & 0x0F) <<  4) |
                           ((value  & 0x0F) <<  0)))

def rst():
    """ set bit 0 of bank 0 to reset the firmware """
    return gpio_backend(write  = 1, 
                        bank   = 0,
                        offset = 0,
                        mask   = 1,
                        value  = 1)

def set_power(update = False, pwr_states = [False]*4):
    """ read or write the bits 4:7 of bank 0 to set the power state """
    bits = bool_to_mask(pwr_states[0:4])
    return gpio_backend(write  = 1 if update else 0,
                        bank   = 0,
                        offset = 4,
                        mask   = 0xF,
                        value  = bits)

def backend_network_set(clear = False):
    """ set or clear bit 2 of bank 0 """
    return gpio_backend(write  = 1,
                        bank   = 0,
                        offset = 2,
                        mask   = 1,
                        value  = 0 if clear else 1)

def gpio_rd_rx_err():
    """ read bits 0:3 of bank 1 """
    return gpio_backend(offset = 0, mask = 0xF)

def gpio_rd_tx_idle():
    """ read bits 4:7 of bank 1 """
    return gpio_backend(offset = 4, mask = 0xF)

def get_current(m):
    return build(m, GET_CURRENT, 0)

def backend_status(val = 0):
    return build(0, NOP, val)

# Frontend commands

def dac_write(module, channel, value):
    channel &= 0xF
    value &= 0xFFF
    return build(module, DAC_WRITE, (0x3 << 16) | (channel << 12) | value)

def adc_read(module, channel):
    channel &= 0xF
    return build(module, ADC_READ, (channel << 16))

def module_id(m):
    return build(m, MODULE_ID, 0)
