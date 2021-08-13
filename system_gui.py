import tkinter as tk
from tkinter.ttk import Separator
from tkinter.scrolledtext import ScrolledText

from backend import Backend

def to_mask(num):
    return format(num, '#06b')

class App(tk.Frame):
    def __init__(self):
        self.root = tk.Tk()
        super().__init__(self.root)
        self.draw()

    def draw(self):
        self.backend_frame = tk.Frame(self.root)
        self.backend_frame.pack()

        self.backend_label = tk.Label(self.backend_frame, text = "Backend")
        self.backend_label.pack(fill = "both", expand = True, padx = 10)

        backend_ips = ['192.168.1.101']
        backend_lab = ['Data']
        
        args = zip([self.backend_frame]*len(backend_ips), backend_lab, backend_ips)
        self.backend = [Backend(*a) for a in args]

        # Refresh backend status
        refresh_callback = lambda: [b.set_status() for b in self.backend]
        self.backend_refresh = tk.Button(self.backend_frame, text = "Refresh", command = refresh_callback)
        self.backend_refresh.pack(fill = "both", expand = True, padx = 10, pady = 10)

        def callback_gen(func, *args):
            return lambda: self.print([to_mask(getattr(b, func)(*args)) for b in self.backend])

        rx_status_callback = callback_gen('get_rx_status')
        tx_status_callback = callback_gen('get_tx_status')
        power_rd_callback  = callback_gen('get_set_frontend_power', False)
        power_wr_callback  = callback_gen('get_set_frontend_power', True)
        current_callback   = lambda: self.print([b.get_current() for b in self.backend])

        self.backend_rx_status = tk.Button(self.backend_frame, text = "Update RX status", command = rx_status_callback)
        self.backend_tx_status = tk.Button(self.backend_frame, text = "Update TX status", command = tx_status_callback)
        self.power_rd_callback = tk.Button(self.backend_frame, text = "Read power state", command = power_rd_callback)
        self.power_wr_callback = tk.Button(self.backend_frame, text = "Set power state", command = power_wr_callback)
        self.current_callback  = tk.Button(self.backend_frame, text = "Read current", command = current_callback)

        self.backend_rx_status.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.backend_tx_status.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.power_rd_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.power_wr_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)
        self.current_callback.pack(fill = "both", expand = True, padx = 10, pady = 10)

        Separator(self.root, orient = "horizontal").pack(fill = tk.X, expand = True, padx = 10, pady = 10)

        self.status_text = ScrolledText(master = self.root, width = 60, height = 10, takefocus = False)
        self.status_text.pack(fill = "both", expand = True, padx = 10, pady = 10)

    def print(self, txt):
        self.status_text.insert(tk.END, str(txt) + "\n")
        self.status_text.yview(tk.END)

app = App()
app.mainloop()
