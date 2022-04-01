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
    def __init__(self, frontend_instance, root):
        self.frontend = frontend_instance

        self.current_label = tk.Label(root, text = "Current:")
        self.temps_label   = tk.Label(root, text = "Temp:")

        self.current_ind = tk.Canvas(root, bg = 'red', height = 10, width = 10)
        self.temps_ind  = [tk.Canvas(root, bg = 'red', height = 10, width = 10) for _ in range(8)]

    def pack(self):
        self.current_label.pack(side = tk.LEFT, padx = 10)
        self.current_ind.pack(side = tk.LEFT)

        self.temps_label.pack(side = tk.LEFT, padx = 10)

        for ts in self.temps_ind:
            ts.pack(side = tk.LEFT, padx = 5, expand = True)

    def set_all_temps(self, temps):
        for t, ind in zip(temps, self.temps_ind):
            col = scale_value(t, 20.0, 30.0)
            ind.config(bg = col)

    def set_current(self, curr):
        col = scale_value(curr, 600, 800)
        self.current_ind.config(bg = col)
