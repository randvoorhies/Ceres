#!/usr/bin/env python

import socket
import time

TCP_IP = '127.0.0.1'
TCP_PORT = 10000

i = 0
while True:
  i += 1;
  if i > 100:
    i = 0
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((TCP_IP, TCP_PORT))

  s.send('hwid : fastdevice\r\n')
  s.send("temperature : {0}\r\n".format(i))
  s.send("humidity : {0}\r\n".format(i))
  s.send("light : {0}\r\n".format(i))

  s.close()

  print i
  time.sleep(1.1)

