import tkinter as tk
from frontend_ui import FrontendUI

class BackendUI():
    def recv_data(self):
        pass

    def __init__(self, backend_instance, parent_frame):
        self.backend = backend_instance
        self.backend.__setattr__("data_output", self.print)

        self.frame = tk.Frame(parent_frame, relief = tk.GROOVE, borderwidth = 1)
        self.common = tk.Frame(self.frame)
        self.frame.pack(fill = tk.X, expand = True, padx = 10, pady = 10)
        self.common.pack(fill = tk.X, expand = True, padx = 10, pady = 10)

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

        self.label  = tk.Label(self.common, text = "Data: {}".format(self.backend.ip))
        self.status = tk.Canvas(self.common, bg = 'red', height = 10, width = 10)
        self.data = tk.Text(master = self.common, height = 5, takefocus = False)

        self.label.pack(side = tk.LEFT, padx = 10)
        self.status.pack(side = tk.LEFT, padx = 10)
        self.data.pack(side = tk.LEFT, padx = 10, pady = 10, expand = True, fill = tk.X)

    def print(self, txt):
        self.data.insert(tk.END, str(txt) + "\n")
        self.data.yview(tk.END)

    def __getattr__(self, attr):
        return getattr(self.backend, attr)

