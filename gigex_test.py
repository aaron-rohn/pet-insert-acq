import socket
import time

c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
c.settimeout(1)
c.connect(('192.168.1.101', 20481))
c.send(0xf1000000.to_bytes(4,'big'))
resp = c.recv(4)
print(hex(resp))
c.close()

time.sleep(1)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1)
s.connect(('192.168.1.101', 5556))

"""
for _ in range(1024):
    s.recv(4096)
"""

s.send(0xf0000000.to_bytes(4,'big'))
buf = s.recv(1024)
#print(buf[3::4])
print(buf)

s.close()
