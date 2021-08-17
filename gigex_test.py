import socket
import time
from gigex import Gigex
import command

g = Gigex('192.168.1.100')

with g:
    g.reboot()
    ret = g.spi_query(command.rst())
    print(hex(ret))
