import tkinter as tk
from toggle_button import ToggleButton

def scale_value(value, minrange, maxrange):
    if value < 0: return 'black'

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

        self.status = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10)
        self.current = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10)
        self.temp_status = [tk.Canvas(self.frame, bg = 'red', height = 10, width = 10) for _ in range(8)]

        tk.Label(self.frame, text = "Status:").pack(side = tk.LEFT, padx = 10)
        self.status.pack(side = tk.LEFT)

        tk.Label(self.frame, text = "Current:").pack(side = tk.LEFT, padx = 10)
        self.current.pack(side = tk.LEFT)

        tk.Label(self.frame, text = "Temp:").pack(side = tk.LEFT, padx = 10)
        [ts.pack(side = tk.LEFT, padx = 10) for ts in self.temp_status]

    def get_temp(self):
        temps = self.frontend.get_temp()

        for t,ts in zip(temps, self.temp_status):
            col = scale_value(t, 20.0, 30.0)
            ts.config(bg = col)

        return temps

    def get_current(self):
        c = self.frontend.get_current()
        col = scale_value(c, 600, 700)
        self.current.config(bg = col)
        return c

    def get_id(self):
        self.frontend.get_physical_idx()
