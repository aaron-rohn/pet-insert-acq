import math

# Map the physical block to the DAC channel
#thresh_channels = { 1: 2, 2: 0, 3: 3, 4: 1 }
#bias_channels   = { 1: 6, 2: 4, 3: 7, 4: 5 }
thresh_channels = { 0: 2, 1: 0, 2: 3, 3: 1 }
bias_channels   = { 0: 6, 1: 4, 2: 7, 3: 5 }

# Map physical block and front/rear thermisor to ADC channel
# First four channels are front, last four are rear
#temp_channels = { 1: 5, 2: 1, 3: 6, 4: 2, 5: 4, 6: 0, 7: 7, 8: 3 }
temp_channels = { 0: 5, 1: 1, 2: 6, 3: 2, 4: 4, 5: 0, 6: 7, 7: 3 }

class Frontend():
    def __init__(self, transfer_cmd, logical_idx):
        self.transfer_cmd = transfer_cmd
        self.failed = False

        # logical_idx should be 0-3, and reflects the port on the backend board
        self.logical_idx = logical_idx & 0xF

        # physical_idx will be 0-15, and reflects the position in the system
        self.physical_idx = 0

    @staticmethod
    def bias_to_hex(target_voltage):
        set_voltage = target_voltage * 1.0075
        return int(set_voltage / 13.0 / 2.5 * 0xFFF)

    @staticmethod
    def thresh_to_hex(voltage):
        return int(voltage * 20.4 / 2.5 * 0xFFF)

    @staticmethod
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

    @staticmethod
    def res_to_temp(R, R0 = 10000, T0 = 298.15, B = 3900):
        """
        Based on the Steinhart-Hart equation
        """
        r_inf = R0 * math.exp(-B / T0)

        try:
            t_kelvin = B / math.log(R / r_inf)
            return t_kelvin - 273.15
        except (ZeroDivisionError, ValueError) as e:
            return 0

    @staticmethod
    def adc_to_temp(adc_val):

        if adc_val is None:
            return None

        adc_val = int(adc_val.hex(), 16) & 0xFFF
        voltage = (adc_val / 0x7FF) * 2.048
        resistance = Frontend.voltage_to_res(voltage)

        return Frontend.res_to_temp(resistance)

    def __transfer_cmd_or_fail(self, cmd):
        ret = None

        if not self.failed:
            ret = self.transfer_cmd(cmd)

        if ret is None:
            self.failed = True

        return ret

    def set_dac(self, is_bias, block, value):

        if (is_bias):
            ch = bias_channels[block]
            val = self.bias_to_hex(value)
        else:
            ch = thresh_channels[block]
            val = self.thresh_to_hex(value)

        cmd = 0xf0130000 | self.logical_idx << 24 | ch << 12 | val
        cmd = bytearray.fromhex('{:08x}'.format(cmd))
        ret = self.__transfer_cmd_or_fail(cmd)

        return (cmd, ret)

    def get_temp(self, channel):
        ch = temp_channels[channel]
        cmd = 0xf0200000 | self.logical_idx << 24 | ch << 16
        cmd = bytearray.fromhex('{:08x}'.format(cmd))
        ret = self.__transfer_cmd_or_fail(cmd)

        return (cmd, ret)

    def get_physical_idx(self):
        cmd = 0xf0300000 | self.logical_idx << 24
        cmd = bytearray.fromhex('{:08x}'.format(cmd))
        ret = self.__transfer_cmd_or_fail(cmd)

        if ret:
            ret = int(ret.hex(), 16)
            ret = (ret >> 24) & 0xF

        return ret

    def get_power(self):
        cmd = 0xf0500000 | self.logical_idx << 24
        cmd = bytearray.fromhex('{:08x}'.format(cmd))
        ret = self.__transfer_cmd_or_fail(cmd)

        ret = int(ret.hex(), 16) & 0xFFFF if ret else None

        # Full scale range of ADC is +/- 2.048V (1mV per LSB)
        # Gain of differential amp is 100
        # Resistance of shunt is 10mOhm
        # Value of ret is in milliamps

        return ret 
