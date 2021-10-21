import tkinter as tk
from toggle_button import ToggleButton

def scale_value(value, minrange, maxrange):
    if value < minrange:
        g = 0xFF
        r = 0x0
    elif value < maxrange:
        off = value - minrange
        diff = maxrange - minrange
        g = round((1.0 - off / diff) * 0xFF)
        r = round(off / diff * 0xFF)
    else:
        g = 0x0
        r = 0xFF

    return '#%02X%02X%02X' % (r, g, 0)

class FrontendUI():
    def __init__(self, frontend_instance, parent_frame):
        self.frontend = frontend_instance
        self.frame = parent_frame

        self.status = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10, text = 'status')
        self.current = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10, text = 'current')
        self.bias = ToggleButton(self.frame, "Bias On", "Bias Off", self.bias_toggle_cb, width = 10)
        self.temp_status = [tk.Canvas(self.frame, bg = 'red', height = 10, width = 10) for _ in range(8)]

        self.status.pack(side = tk.LEFT, padx = 10)
        self.current.pack(side = tk.LEFT, padx = 10)
        self.bias.pack(side = tk.LEFT)
        [ts.pack(side = tk.LEFT, padx = 20) for ts in self.temp_status]

    def bias_toggle_cb(self, turn_on = False, on_val = 29.5):
        on_val = min(29.5, on_val)
        bias_val = on_val if turn_on else 0.0
        self.frontend.set_bias(bias_val)

    def get_temp(self):
        temps = self.frontend.get_temp()
        for t,ts in zip(temps, self.temp_status):
            col = scale_value(t, 20.0, 30.0)
            ts.config(bg = col)

    def get_current(self):
        c = self.frontend.get_current()
        col = scale_value(c, 600, 800)
        self.current.config(bg = col)

    def get_id(self):
        self.frontend.get_physical_idx()
