# -*- coding: utf-8 -*-
"""
Created on Tue Feb 10 14:09:07 2026

@author: 32474
"""

import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", 9000))
print("Listening on 127.0.0.1:9000")
while True:
    data, addr = sock.recvfrom(65536)
    print("FROM", addr, ":", data.decode("utf-8"))
