import command
import math

class Frontend():
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

    def __init__(self, backend_instance, index):
        self.backend = backend_instance
        self.index = index

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
        try:
            r_inf = R0 * math.exp(-B / T0)
            t_kelvin = B / math.log(R / r_inf)
            return t_kelvin - 273.15
        except (ZeroDivisionError, ValueError) as e:
            return 0

    @staticmethod
    def adc_to_temp(adc_val):
        voltage = (adc_val / 0x7FF) * 2.048
        resistance = Frontend.voltage_to_res(voltage)
        return Frontend.res_to_temp(resistance)

    def set_dac(self, is_bias, block, value):
        if (is_bias):
            ch, val = Frontend.bias_ch[block], self.bias_to_hex(value)
        else:
            ch, val = Frontend.thresh_ch[block], self.thresh_to_hex(value)

        cmd = command.dac_write(self.index, ch, val)
        ret = self.backend.exec(cmd)
        return ret

    def get_temp(self):
        temps = []
        for adc_ch in Frontend.temp_channels.values():
            cmd = command.adc_read(self.index, adc_ch)
            ret = self.backend.exec(cmd)
            ret = Frontend.adc_to_temp(ret & 0xFFF)
            temps.append(ret)
        return temps

    def get_physical_idx(self):
        cmd = command.module_id(self.index)
        ret = self.backend.exec(cmd)
        return command.module(ret)
