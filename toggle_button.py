import tkinter as tk

OFF = tk.RAISED
ON  = tk.SUNKEN

class ToggleButton(tk.Button):
    def __init__(self, parent, on_txt, off_txt, cmd, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_txt = on_txt
        self.off_txt = off_txt
        self.cmd = cmd
        self.config(relief = OFF, text = self.off_txt, command = self.on_click)

    def on_click(self):
        curr_state = self.config('relief')[-1]
        if curr_state == ON:
            self.cmd(False)
            self.config(relief = OFF, text = self.off_txt)
        else:
            self.cmd(True)
            self.config(relief = ON, text = self.on_txt)

