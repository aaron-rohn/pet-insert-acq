#!/usr/bin/python3

import logging
from system import System
from system_ui import SystemUI

if __name__ == "__main__":
    logging.basicConfig(level = logging.INFO)
    sys = System()
    app = SystemUI(sys)
    with sys:
        app.root.mainloop()
