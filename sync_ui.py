import threading
import tkinter as tk
from sync import Sync
from toggle_button import ToggleButton

class SyncUI():
    def __init__(self, sync_instance, root):
        self.sync = sync_instance

        self.frame  = tk.Frame(root, relief = tk.GROOVE, borderwidth = 1)

        self.label  = tk.Label(self.frame,
                text = "Sync: {}".format(self.sync.ip))

        self.status_ind = tk.Canvas(self.frame, 
                bg = 'red', height = 10, width = 10)

        self.rst_button = tk.Button(self.frame, 
                text = "Align Time Tags", 
                command = self.sync_reset)

        self.air_tog = ToggleButton(self.frame,
                "Air ON", "Air OFF", self.toggle_air)

    def pack(self):
        self.frame.pack(side = tk.TOP, anchor = tk.N,
                padx = 10, pady = 10, fill = tk.X)

        self.label.pack(side = tk.LEFT, padx = 10, pady = 10)
        self.status_ind.pack(side = tk.LEFT, padx = 10, pady = 10)
        self.rst_button.pack(side = tk.LEFT, padx = 10, pady = 10)
        self.air_tog.pack(side = tk.LEFT, padx = 10, pady = 10)

    def sync_reset(self):
        threading.Thread(target = self.sync.sync_reset).start()

    def toggle_air(self, turn_on = False):
        #self.sync.toggle_dac(turn_on)
        if turn_on:
            self.sync.track_temp_start()
        else:
            self.sync.track_temp_stop()
