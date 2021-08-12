import socket
import time
from gigex import Gigex
from command import Command

g = Gigex('192.168.1.101')

with g:
    g.reboot()

with g:
    ret = g.spi_query(Command.set_power())
    print(hex(ret))

    time.sleep(0.5)

    ret = g.spi_query(Command.set_power(True))
    print(hex(ret))

    time.sleep(0.5)

    ret = g.spi_query(Command.set_power())
    print(hex(ret))

