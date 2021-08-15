import tkinter as tk

class FrontendUI():
    def __init__(self, frontend_instance, parent_frame):
        self.frontend = frontend_instance
        self.frame = parent_frame

        self.status = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10)
        self.bias = tk.Button(self.frame, text = "Bias", command = self.set_bias)
        self.thresh = tk.Button(self.frame, text = "Threshold", command = self.set_thresh)
        self.temp = tk.Button(self.frame, text = "Temperature", command = self.get_temp)
        self.id = tk.Button(self.frame, text = "ID", command = self.get_id)

        self.status.pack(side = tk.LEFT, padx = 10)
        self.bias.pack(side = tk.LEFT)
        self.thresh.pack(side = tk.LEFT)
        self.temp.pack(side = tk.LEFT)
        self.id.pack(side = tk.LEFT)

    def set_bias(self):
        self.frontend.set_dac(True, 0, 0)

    def set_thresh(self):
        self.frontend.set_dac(False, 0, 0)

    def get_temp(self):
        temps = self.frontend.get_temp()
        print(temps)

    def get_id(self):
        self.frontend.get_physical_idx()
