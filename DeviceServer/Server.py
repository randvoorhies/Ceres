#!/usr/bin/env python

from twisted.internet import protocol, reactor
from twisted.internet.protocol import Factory

class DeviceServer(protocol.Protocol):
  def dataReceived(self, data):
    print data
    self.transport.write(data)
    self.transport.loseConnection()

factory = Factory()
factory.protocol = DeviceServer
reactor.listenTCP(10000, factory)
reactor.run()

