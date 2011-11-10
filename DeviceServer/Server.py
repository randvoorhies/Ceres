#!/usr/bin/env python

from twisted.internet import protocol, reactor
from twisted.internet.protocol import Factory
from twisted.python import log

class DeviceServer(protocol.Protocol):
  def connectionMade(self):
    log.msg('New Connection: ' + str(self.transport.getHost()))

  def dataReceived(self, data):
    self.transport.write(data)
    self.transport.loseConnection()

log.startLogging(open('/var/log/ceres.log', 'w'))
factory = Factory()
factory.protocol = DeviceServer
reactor.listenTCP(10000, factory)
reactor.run()

