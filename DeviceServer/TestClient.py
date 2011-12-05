#!/usr/bin/env python

import socket
import time
import random

TCP_IP = '127.0.0.1'
TCP_PORT = 10000

i = 0
while True:
  i += 1;
  if i > 100:
    i = 0
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((TCP_IP, TCP_PORT))

  temperature = 100-i+random.randint(-10, 10)
  humidity = (50+i)%100+random.randint(-5, 5)
  light = i + random.randint(-20, 20)

  print "temperature : {0}\r\n".format(temperature)
  print "humidity : {0}\r\n".format(humidity)
  print "light : {0}\r\n".format(light)

  s.send('hwid : gooddevice\r\n')
  s.send("temperature : {0}\r\n".format(temperature))
  s.send("humidity : {0}\r\n".format(humidity))
  s.send("light : {0}\r\n".format(light))

  s.close()

  print i
  time.sleep(1.5)

