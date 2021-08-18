import tkinter as tk
from toggle_button import ToggleButton

class FrontendUI():
    def __init__(self, frontend_instance, parent_frame):
        self.frontend = frontend_instance
        self.frame = parent_frame

        self.status = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10)
        # TODO show current consumption next to status indicator?
        self.bias = ToggleButton(self.frame, "Bias On", "Bias Off", self.bias_toggle_cb, width = 10)
        self.temp = tk.Button(self.frame, text = "Temperature", command = self.get_temp)
        self.temp_status = [tk.Canvas(self.frame, bg = 'red', height = 10, width = 10) for _ in range(8)]

        self.status.pack(side = tk.LEFT, padx = 10)
        self.bias.pack(side = tk.LEFT)
        self.temp.pack(side = tk.LEFT)
        [ts.pack(side = tk.LEFT, padx = 20) for ts in self.temp_status]

    def bias_toggle_cb(self, turn_on = False):
        bias_val = 29.5 if turn_on else 0.0
        self.frontend.set_bias(bias_val)

    def get_temp(self, minrange = 20.0, maxrange = 30.0):
        temps = self.frontend.get_temp()
        print(temps)
        for t,ts in zip(temps, self.temp_status):
            if minrange < t < maxrange:
                g = round((1.0 - (t - minrange) / (maxrange - minrange)) * 0xFF)
                r = round((t - minrange) / (maxrange - minrange) * 0xFF)
            else:
                g = 0
                r = 0

            col = '#%02X%02X%02X' % (r, g, 0)
            ts.config(bg = col)
            # TODO show text next to color indicator?

    def get_id(self):
        self.frontend.get_physical_idx()
