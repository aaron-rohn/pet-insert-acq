import tkinter as tk
from sync import Sync

class SyncUI():
    def __init__(self, sync_instance, parent_frame):
        self.sync = sync_instance
        self.frame = tk.Frame(parent_frame, relief = tk.GROOVE, borderwidth = 1)
        self.label = tk.Label(self.frame, text = "Sync: {}".format(self.sync.ip))
        self.status = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10)
        self.rst = tk.Button(self.frame, text = "Align Time Tags", command = self.sync.rst)

        self.frame.pack(fill = tk.X, expand = True, padx = 10, pady = 10)
        self.label.pack(side = tk.LEFT, padx = 10, pady = 10)
        self.status.pack(side = tk.LEFT, padx = 10, pady = 10)
        self.rst.pack(side = tk.LEFT, padx = 10, pady = 10)
