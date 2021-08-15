import tkinter as tk
from backend import Backend

class BackendUI():
    def __init__(self, backend_instance, parent_frame):
        self.backend = backend_instance
        self.backend.__setattr__("data_output", self.print)
        self.m_pow_var = [tk.IntVar() for _ in range(4)]

        self.frame  = tk.Frame(parent_frame)
        self.label  = tk.Label(self.frame, text = self.backend.label_text+ ":")
        self.text   = tk.Label(self.frame, text = self.backend.ip)
        self.status = tk.Canvas(self.frame, bg = 'red', height = 10, width = 10)
        self.m_pow  = [tk.Checkbutton(self.frame, text = i, variable = self.m_pow_var[i]) for i in range(4)]
        self.data = tk.Text(master = self.frame, height = 5, takefocus = False)

        self.frame.pack(fill = tk.X, expand = True, padx = 10, pady = 10)
        self.label.pack(side = tk.LEFT)
        self.text.pack(side = tk.LEFT)
        self.status.pack(side = tk.LEFT, padx = 10)
        [m.pack(side = tk.LEFT) for m in self.m_pow]
        self.data.pack(side = tk.LEFT, padx = 10, expand = True, fill = tk.X)

    def print(self, txt):
        self.data.insert(tk.END, str(txt) + "\n")
        self.data.yview(tk.END)

    def __getattr__(self, attr):
        return getattr(self.backend, attr)

