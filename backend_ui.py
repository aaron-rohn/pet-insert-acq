import os
import tkinter as tk
from tkinter import filedialog
from contextlib import ExitStack
from frontend_ui import FrontendUI

class BackendUI():
    def update_output_dir(self):
        dirname = filedialog.askdirectory()
        fun = self.print

        try:
            if not dirname: raise Exception('No file selected')
            fname = dirname + '/' + self.ip + '.dat'

            with ExitStack() as stack:
                f = stack.enter_context(open(fname, 'wb'))
                self._stack = stack.pop_all()
                fun = lambda data: f.write(data)
                self.file_indicator.config(text = fname)

        except Exception as e:
            self.file_indicator.config(text = str(e))

        finally:
            self.backend.wr_func.set(fun)

    def __init__(self, backend_instance, parent_frame):
        # Now that an output field exists for the backend, update the write function
        self.backend = backend_instance
        self.backend.wr_func.set(self.print)
        self.frame = tk.Frame(parent_frame, relief = tk.GROOVE, borderwidth = 1)
        self.frame.pack(fill = tk.X, expand = True, padx = 10, pady = 10)

        # Frame with Label, status, and data output text field
        self.common = tk.Frame(self.frame)
        self.common.pack(fill = tk.X, expand = True)
        self.label  = tk.Label(self.common, text = "Data: {}".format(self.backend.ip))
        self.status = tk.Canvas(self.common, bg = 'red', height = 10, width = 10)
        self.data = tk.Text(master = self.common, height = 2, takefocus = False)
        self.label.pack(side = tk.LEFT, padx = 10)
        self.status.pack(side = tk.LEFT, padx = 10)
        self.data.pack(side = tk.LEFT, padx = 10, pady = 10, expand = True, fill = tk.X)

        # Frame with Directory select button, indicator of current directory
        self.file_output = tk.Frame(self.frame)
        self.file_output.pack(fill = tk.X, expand = True)
        self.file_select = tk.Button(self.file_output, text = "Directory", command = self.update_output_dir)
        self.file_indicator = tk.Label(self.file_output, bg = 'white', text = '', anchor = 'w', relief = tk.SUNKEN, borderwidth = 1, height = 2) 
        self.file_select.pack(side = tk.LEFT, padx = 10, pady = 10)
        self.file_indicator.pack(side = tk.LEFT, fill = tk.X, expand = True, padx = 10, pady = 10)

        self.m_pow_var = []
        self.m_pow = []
        self.m_frame = []
        self.frontend = []

        for i in range(4):
            self.m_pow_var.append(tk.IntVar())
            self.m_frame.append(tk.Frame(self.frame))
            self.m_pow.append(tk.Checkbutton(self.m_frame[-1], text = i, variable = self.m_pow_var[-1]))
            self.m_frame[-1].pack(fill = tk.X, expand = True)
            self.m_pow[-1].pack(side = tk.LEFT)

            fe = self.backend.frontend[i]
            self.frontend.append(FrontendUI(fe, self.m_frame[-1]))

    def print(self, txt):
        self.data.insert(tk.END, str(txt) + "\n")
        self.data.yview(tk.END)

    def __getattr__(self, attr):
        return getattr(self.backend, attr)

