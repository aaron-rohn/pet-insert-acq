import tkinter as tk
from sync import Sync

class SyncUI():
    def __getattr__(self, attr):
        return getattr(self.sync, attr)

    def __init__(self, sync_instance, root):
        self.sync = sync_instance

        self.frame  = tk.Frame(root, relief = tk.GROOVE, borderwidth = 1)
        self.label  = tk.Label(self.frame, text = "Sync: {}".format(self.sync.ip))
        self.status_ind = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10)
        self.rst_button = tk.Button(self.frame, text = "Align Time Tags", command = self.sync.sync_reset)

    def pack(self):
        self.frame.pack(side = tk.TOP, anchor = tk.N,
                padx = 10, pady = 10, fill = tk.X)

        self.label.pack(side = tk.LEFT, padx = 10, pady = 10)
        self.status_ind.pack(side = tk.LEFT, padx = 10, pady = 10)
        self.rst_button.pack(side = tk.LEFT, padx = 10, pady = 10)
