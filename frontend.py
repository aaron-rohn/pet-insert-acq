import command
import math

from gigex import ignore_network_errors

BIAS_ON  = 29.5
BIAS_OFF = 0.0

# Map the physical block to the DAC channel
thresh_ch = { 0: 2, 1: 0, 2: 3, 3: 1 }
bias_ch   = { 0: 6, 1: 4, 2: 7, 3: 5 }

# Map physical block and front/rear thermisor to ADC channel
# First four channels are front, last four are rear
temp_channels = { 0: 5, 
                  1: 1,
                  2: 6,
                  3: 2,
                  4: 4,
                  5: 0,
                  6: 7,
                  7: 3 }

def bias_to_hex(target_voltage):
    set_voltage = target_voltage * 1.0075
    return int(set_voltage / 13.0 / 2.5 * 0xFFF)

def thresh_to_hex(voltage):
    return int(voltage * 20.4 / 2.5 * 0xFFF)

def voltage_to_res(Vout, Vin = 2.5, Rs = 10000):
    """
    Rs is the resistance of the reference resistor
    which is on the upper side of the voltage divider
    """
    try:
        Rt = ((Vout * Rs) / Vin) / (1 - (Vout / Vin))
    except ZeroDivisionError as e:
        print("Caught divide by zero: %s" % e.__repr__())
        Rt = float('Inf')

    return Rt

def res_to_temp(R, R0 = 10000, T0 = 298.15, B = 3900):
    """
    Based on the Steinhart-Hart equation
    """
    try:
        r_inf = R0 * math.exp(-B / T0)
        t_kelvin = B / math.log(R / r_inf)
        return t_kelvin - 273.15
    except (ZeroDivisionError, ValueError) as e:
        return 0

def adc_to_temp(adc_val):
    if adc_val < 0: return adc_val
    voltage = ((adc_val & 0xFFF) / 0x7FF) * 2.048
    resistance = voltage_to_res(voltage)
    return res_to_temp(resistance)

class Frontend():
    def __init__(self, backend_instance, index):
        self.backend = backend_instance
        self.index = index

    @ignore_network_errors([-1]*4)
    def set_bias(self, value = 0.0):
        return [self.set_dac(True, i, value) for i in range(4)]

    @ignore_network_errors([-1]*4)
    def get_bias(self):
        return [hex(self.get_dac(True, i)) for i in range(4)]

    @ignore_network_errors([-1]*4)
    def set_thresh(self, value = 0.05):
        return [self.set_dac(False, i, value) for i in range(4)]

    @ignore_network_errors([-1]*4)
    def get_thresh(self):
        return [hex(self.get_dac(False, i)) for i in range(4)]

    def set_dac(self, is_bias, block, value):
        ch, val = ((  bias_ch[block],   bias_to_hex(value)) if is_bias else
                   (thresh_ch[block], thresh_to_hex(value)))

        cmd = command.dac_write(self.index, ch, val)
        ret = self.backend.gx.send(cmd)
        return command.payload(ret)

    def get_dac(self, is_bias, block):
        ch = bias_ch[block] if is_bias else thresh_ch[block]
        cmd = command.dac_read(self.index, ch)
        ret = self.backend.gx.send(cmd)
        return command.payload(ret)

    @ignore_network_errors([-1]*4)
    def get_temp(self):
        temps = []

        for adc_ch in temp_channels.values():
            cmd = command.adc_read(self.index, adc_ch)
            ret = self.backend.gx.send(cmd)
            ret = adc_to_temp(ret)
            temps.append(ret)

        return temps

    @ignore_network_errors(-1)
    def get_physical_idx(self):
        cmd = command.module_id(self.index)
        ret = self.backend.gx.send(cmd)
        return command.module(ret)

    @ignore_network_errors(-1)
    def get_current(self):
        cmd = command.get_current(self.index & 0x3)
        ret = self.backend.gx.send(cmd)
        return command.payload(ret)

    @ignore_network_errors(-1)
    def get_period(self, divisor = 0):
        cmd = command.period_read(self.index, divisor)
        ret = self.backend.gx.send(cmd)
        return command.payload(ret)

    def get_singles_rate(self, block, divisor = 0):
        cmd = command.singles_rate_read(self.index, block, divisor)
        ret = self.backend.gx.send(cmd)
        return command.payload(ret)

    @ignore_network_errors([-1]*4)
    def get_all_singles_rates(self, divisor = 0):
        return [self.get_singles_rate(i, divisor) for i in range(4)]

    @ignore_network_errors(None)
    def frontend_reset(self):
        with self.backend.gx:
            cmd = command.frontend_rst(self.index)
            self.backend.gx._spi(cmd)

    @ignore_network_errors(-1)
    def tt_stall_disable(self, disable = True):
        cmd = command.frontend_tt_stall_disable(
                self.index, int(disable))
        ret = self.backend.gx.send(cmd)
        return command.payload(ret)

    @ignore_network_errors(-1)
    def detector_disable(self, disable = True):
        cmd = command.frontend_det_disable(
                self.index, int(disable))
        ret = self.backend.gx.send(cmd)
        return command.payload(ret)
