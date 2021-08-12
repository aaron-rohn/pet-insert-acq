import socket
from gigex import Gigex

g = Gigex('192.168.1.101')

with g:

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    s.connect(('192.168.1.101', 5556))

    try:
        for _ in range(1024):
            s.recv(4096)
    except:
        pass

    ret = g.spi(0x4)
    print(ret)

    buf = s.recv(4096)
    print(buf)

    s.close()

