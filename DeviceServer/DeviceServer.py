#!/usr/bin/env python

from twisted.internet import protocol, reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.python import log
import twisted.python
import pymongo
import rrdtool
import threading
import time, datetime, calendar

######################################################################
class ProtocolException(Exception):
  def __init__(self, reason, fatal):
    self.reason = reason
    self.fatal = fatal

######################################################################
class DeviceProtocol(LineReceiver):
  def connectionMade(self):
    self.now = int(calendar.timegm(time.gmtime()))
    self.lines = 0
    self.data = {}
    self.hwid = ''

  ######################################################################
  def connectionLost(self, reason):
    if len(self.data) == 0:
      return

    templatestr = '--template='
    for dsid in self.data.keys():
      templatestr += dsid + ':'
    templatestr = templatestr[0:-1]

    nowstr = str(int(calendar.timegm(time.gmtime())))

    datastr = nowstr
    for value in self.data.values():
      datastr += ':' + value
    
    rrdlock.acquire()
    try:
      ret = rrdtool.update(str(self.rrdfile), templatestr, datastr)
    except rrdtool.error as e:
      log.msg('Error writing to rrdfile for hwid [' + self.hwid +']: ' + str(e))
    finally:
      rrdlock.release()

  ######################################################################
  def lineReceived(self, data):
    global ceresdb

    self.lines += 1

    try:
      datasplit = data.split(':')
      if len(datasplit) == 2:
        key = datasplit[0].strip()
        val = datasplit[1].strip()

        if self.lines == 1:
          # The first line must contain 'hwid : ????????' to identify the
          # device.  Make sure this line is properly formatted, extract the
          # hwid, and look it up in the database

          if key == 'hwid':
            deviceinfo = ceresdb.devices.find_one({'hwid' : val})
            if deviceinfo == None:
              raise ProtocolException(reason='Unknown hwid [' + val + ']', fatal=True)
            else:
              self.hwid = val
              self.rrdfile = deviceinfo['file']

        else:
          # All subsequent lines must be of the form 'S : D', where S is the
          # name of a data source, and D is the data value.
          dsid = key

          # Make sure the data value is a floating point number
          try: float(val)
          except ValueError: raise ProtocolException(reason='Invalid data value [' + val + ']', fatal=False)

          self.data[dsid] = val

      else:
        raise ProtocolException(reason='Invalid Data - too many fields [' + data + ']', fatal=False)

    except ProtocolException as e:
      log.msg(str(self.transport.getHost()) + ' Exception: ' + e.reason)
      if e.fatal:
        self.transport.loseConnection()


######################################################################
log.startLogging(open('/var/log/ceres.log', 'w'))

dbconnection = pymongo.Connection()
ceresdb = dbconnection.ceres

rrdlock = threading.Lock()

factory = Factory()
factory.protocol = DeviceProtocol
#reactor.listenTCP(10000, factory, interface='192.168.1.1')
reactor.listenTCP(10000, factory)
reactor.run()

