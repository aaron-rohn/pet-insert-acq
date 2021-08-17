import tkinter as tk

class FrontendUI():
    def __init__(self, frontend_instance, parent_frame):
        self.frontend = frontend_instance
        self.frame = parent_frame

        self.status = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10)
        self.bias_on = tk.Button(self.frame, text = "Bias On", command = lambda: self.set_bias(29.5))
        self.bias_off = tk.Button(self.frame, text = "Bias Off", command = self.set_bias)
        self.temp = tk.Button(self.frame, text = "Temperature", command = self.get_temp)

        self.status.pack(side = tk.LEFT, padx = 10)
        self.bias_on.pack(side = tk.LEFT)
        self.bias_off.pack(side = tk.LEFT)
        self.temp.pack(side = tk.LEFT)

    def set_bias(self, bias = 0.0):
        [self.frontend.set_dac(True, i, bias) for i in range(4)]

    def set_thresh(self, thresh = 0.50):
        [self.frontend.set_dac(False, i, thresh) for i in range(4)]

    def get_temp(self):
        temps = self.frontend.get_temp()
        print(temps)

    def get_id(self):
        self.frontend.get_physical_idx()
