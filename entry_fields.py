import tkinter as tk

class NumericEntry(tk.Entry):
    def validate(self, new_value):
        try:
            if len(new_value) > 0: float(new_value)
            return True
        except ValueError:
            return False

    def get(self):
        val = super().get()
        return float(val) if len(val) > 0 else self.default

    def __init__(self, root, default, callback, **kwds):
        self.default = default
        vcmd = (root.register(self.validate), '%P')
        super().__init__(root, validate = 'key', validatecommand = vcmd, **kwds)
        self.bind('<Return>', lambda ev: callback())

class BiasEntry(NumericEntry):
    def validate(self, new_value):
        pass

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
