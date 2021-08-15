import tkinter as tk

class FrontendUI():
    def __init__(self, frontend_instance, parent_frame):
        self.frontend = frontend_instance
        self.frame = parent_frame

        self.bias   = tk.Button(self.frame, text = "Bias")
        self.thresh = tk.Button(self.frame, text = "Threshold")
        self.temp   = tk.Button(self.frame, text = "Temperature")

        self.bias.pack(side = tk.LEFT)
        self.thresh.pack(side = tk.LEFT)
        self.temp.pack(side = tk.LEFT)

