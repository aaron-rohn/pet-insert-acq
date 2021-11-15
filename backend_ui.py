import os
import contextlib
import tkinter as tk
from tkinter import filedialog
from frontend_ui import FrontendUI

class BackendUI():

    def __getattr__(self, attr):
        return getattr(self.backend, attr)

    def update_ui_elements(self):
        temps = []
        currents = []

        for f in self.frontend:
            t = f.get_temp()
            c = f.get_current()

            temps += t
            currents += [c]

        return temps, currents

    def update_output_dir(self):
        try:
            dirname = filedialog.askdirectory()
            if not dirname: raise Exception('No file selected')
            fname = dirname + '/' + self.ip + '.SGL'
            self.backend.file_queue.put(fname)
            self.backend.ui_queue.put(None)
            self.file_indicator.config(text = fname)
        except Exception as e:
            self.file_indicator.config(text = str(e))
            self.backend.file_queue.put(os.devnull)
            self.backend.ui_queue.put(self.data)

        self.backend.update_queue.set()

    def __init__(self, backend_instance, parent_frame):
        self.backend = backend_instance
        self.frame = tk.Frame(parent_frame, relief = tk.GROOVE, borderwidth = 1)
        self.frame.pack(fill = tk.X, expand = True, padx = 10, pady = 10)

        # Frame with Label, status, and data output text field
        self.common = tk.Frame(self.frame)
        self.label  = tk.Label(self.common, text = f'Data: {self.backend.ip}')
        self.rst    = tk.Button(self.common, text = "Reset", command = self.backend.reset)
        self.status = tk.Canvas(self.common, bg = 'red', height = 10, width = 10)
        self.data   = tk.Text(self.common, height = 2, takefocus = False)

        self.common.pack(fill = tk.X, expand = True)
        self.label.pack(side = tk.LEFT, padx = 5)
        self.rst.pack(side = tk.LEFT, padx = 5)
        self.status.pack(side = tk.LEFT, padx = 5)
        self.data.pack(side = tk.LEFT, padx = 5, pady = 10, expand = True, fill = tk.X)

        # Now that an output field exists for the backend, update the write function
        self.backend.ui_queue.put(self.data)
        self.backend.update_queue.set()

        # Frame with Directory select button, indicator of current directory
        self.file_output    = tk.Frame(self.frame)
        self.file_select    = tk.Button(self.file_output, text = "Directory", command = self.update_output_dir)
        self.file_indicator = tk.Label(self.file_output, bg = 'white', text = '', anchor = 'w', relief = tk.SUNKEN, borderwidth = 1, height = 2) 

        self.file_output.pack(fill = tk.X, expand = True)
        self.file_select.pack(side = tk.LEFT, padx = 10, pady = 10)
        self.file_indicator.pack(side = tk.LEFT, fill = tk.X, expand = True, padx = 10, pady = 10)

        # Populate items for the four frontend instances

        self.m_pow_var = []
        self.m_pow = []
        self.m_frame = []
        self.frontend = []

        for i in range(4):
            self.m_pow_var.append(tk.IntVar())
            self.m_frame.append(tk.Frame(self.frame))

            cb = tk.Checkbutton(self.m_frame[-1],
                                text = str(i).rjust(2),
                                variable = self.m_pow_var[-1],
                                font = 'TkFixedFont')

            self.m_pow.append(cb)
            self.m_frame[-1].pack(fill = tk.X, expand = True)
            self.m_pow[-1].pack(side = tk.LEFT)

            fe = self.backend.frontend[i]
            self.frontend.append(FrontendUI(fe, self.m_frame[-1]))

        # allow the backend instance to update the frontend temperature indicators
        self.backend.__setattr__('mon_cb', self.update_ui_elements)

