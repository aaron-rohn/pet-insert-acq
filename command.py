def mask_to_bool(val, n = 4):
    return [bool(val & (1 << i)) for i in range(n)]

def bool_to_mask(bits):
    value = 0
    for i,v in enumerate(bits):
        value |= (int(v) << i)
    return value

RST = 0x0

# Frontend commands
DAC_WRITE       = 0x1
ADC_READ        = 0x2
MODULE_ID       = 0x3
DAC_READ        = 0x8
PERIOD_READ     = 0x9
SGL_RATE_READ   = 0xA
GPIO_FRONEND    = 0xB

# Backend commands
SET_POWER       = 0x4
GET_CURRENT     = 0x5
GPIO            = 0x6
NOP             = 0x7
COUNTER_READ    = 0xC
UPDATE_REG      = 0xD

CMD_RESPONSE    = 0xF

CMD_EMPTY = 0xF0000000

def payload(cmd_int):
    return cmd_int & 0xFFFFF

def command(cmd_int):
    return (cmd_int >> 20) & 0xF if cmd_int >= 0 else cmd_int

def module(cmd_int):
    return (cmd_int >> 24) & 0xF if cmd_int >= 0 else cmd_int

def build(m, c, p):
    return CMD_EMPTY | ((m & 0xF) << 24) | ((c & 0xF) << 20) | (p & 0xFFFFF)

def is_command(cmd_int):
    return (cmd_int >> 28) == 0xF

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

def rst_soft(clear = True):
    """ set bit 0 of bank 0 to reset all backend components except
    for the microblaze - this retains the module power states
    """
    return gpio_backend(write  = 1, 
                        bank   = 0,
                        offset = 0,
                        mask   = 1,
                        value  = 0 if clear else 1)
    
def rst_hard():
    """ set bit 3 of bank 0 to reset all backend components
    including the microblaze, powering off the frontend
    """
    return gpio_backend(write  = 1, 
                        bank   = 0,
                        offset = 3,
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

def backend_counter(module, channel):
    """ read a counter for the specified module
    The channel value corresponds to:
    0 -> single events
    1 -> timetags
    2 -> commands from frontend
    The corresponding counter is reset upon reading
    """
    return build(module, COUNTER_READ, channel)

def backend_reg_update(otp = True, ocp = True, thr = 1500):
    return build(0, UPDATE_REG,
                 int(otp) << 13 | int(ocp) << 12 | thr & 0xFFF)

# Frontend commands

def dac_write(module, channel, value):
    channel &= 0xF
    value &= 0xFFF
    pld = (0x3 << 16) | (channel << 12) | value
    return build(module, DAC_WRITE, pld)

def dac_read(module, channel):
    return build(module, DAC_READ, (channel & 0xF) << 12)

def adc_read(module, channel):
    channel &= 0xF
    return build(module, ADC_READ, (channel << 16))

def module_id(module):
    return build(module, MODULE_ID, 0)

def period_read(module, divisor = 0):
    # divisor indicates a number of bits to right shift out before returning
    return build(module, PERIOD_READ, divisor & 0xFF)

def singles_rate_read(module, block, divisor = 16):
    pld = ((block & 0x3) << 8) | (divisor & 0xFF)
    return build(module, SGL_RATE_READ, pld)

def gpio_frontend(module, write, offset, mask, value):
    return build(module, GPIO_FRONEND,
            (((write  & 0x03) << 18) |
             ((offset & 0xFF) <<  8) |
             ((mask   & 0x0F) <<  4) |
             ((value  & 0x0F) <<  0)))

def frontend_rst(module):
    return gpio_frontend(module,
            write  = 1,
            offset = 4,
            mask   = 1,
            value  = 1)

def frontend_tt_stall_disable(module, disable = 1):
    return gpio_frontend(module,
            write  = 1,
            offset = 2,
            mask   = 1,
            value  = disable)

def frontend_det_disable(module, disable = 1):
    return gpio_frontend(module,
            write  = 1,
            offset = 3,
            mask   = 1,
            value  = disable)

def frontend_otp_thresh(m, thr):
    return build(m, UPDATE_REG, (0xF << 16) | (thr & 0xFFFF))
