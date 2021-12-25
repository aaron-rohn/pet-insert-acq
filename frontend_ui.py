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
    def __getattr__(self, attr):
        return getattr(self.frontend, attr)

    def __init__(self, frontend_instance, root):
        self.frontend = frontend_instance

        self.status_label  = tk.Label(root, text = "Status:")
        self.current_label = tk.Label(root, text = "Current:")
        self.temps_label   = tk.Label(root, text = "Temp:")

        self.status_ind  = tk.Canvas(root, bg = 'red', height = 10, width = 10)
        self.current_ind = tk.Canvas(root, bg = 'red', height = 10, width = 10)
        self.temps_ind  = [tk.Canvas(root, bg = 'red', height = 10, width = 10) for _ in range(8)]

    def pack(self):
        self.status_label.pack(side = tk.LEFT, padx = 10)
        self.status_ind.pack(side = tk.LEFT)

        self.current_label.pack(side = tk.LEFT, padx = 10)
        self.current_ind.pack(side = tk.LEFT)

        self.temps_label.pack(side = tk.LEFT, padx = 10)
        [ts.pack(side = tk.LEFT, padx = 5, expand = True) for ts in self.temps_ind]

    def get_temp(self):
        temp_vals = self.frontend.get_temp()

        for t,ts in zip(temp_vals, self.temps_ind):
            col = scale_value(t, 20.0, 30.0)
            ts.config(bg = col)

        return temp_vals 

    def get_current(self):
        c = self.frontend.get_current()
        col = scale_value(c, 600, 700)
        self.current_ind.config(bg = col)
        return c

    def get_id(self):
        self.frontend.get_physical_idx()
