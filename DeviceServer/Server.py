#!/usr/bin/env python

from twisted.internet import protocol, reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.python import log
import pymongo
import datetime

class ProtocolException(Exception):
  def __init__(self, reason, fatal):
    self.reason = reason
    self.fatal = fatal

class DeviceProtocol(LineReceiver):
  def connectionMade(self):
    self.now = datetime.datetime.utcnow()
    self.lines = 0
    log.msg('New Connection: ' + str(self.transport.getHost()))

  def lineReceived(self, data):
    global ceresdb

    self.lines += 1

    try:
      datasplit = data.split(':')
      if len(datasplit) == 2:
        key = datasplit[0].strip()
        val = datasplit[1].strip()

        if self.lines == 1:
          # The first line must contain 'hwid : ????????' to identify the device. 
          # Make sure this line is properly formatted, extract the hwid, and look it up in the database

          if key == 'hwid':
            deviceinfo = ceresdb.devices.find_one({'hwid' : val})
            if deviceinfo == None:
              raise ProtocolException(reason='Unknown hwid [' + val + ']', fatal=True)
            else:
              self.hwid = val
              log.msg('Got connection from host [' + str(self.transport.getHost()) + '] hwid [' + val + ']')
        else:
          # All subsequent lines must be of the form 'N : D', where N is a data source id, and D is a data value.

          dsid = None
          try: dsid = int(key)
          except ValueError: raise ProtocolException(reason='Invalid data source id [' + key + ']', fatal=False)

          data = None
          try: data = float(val)
          except ValueError: raise Exception(reason='Invalid data value id [' + val + ']', fatal=False)

          # Ensure that we haven't recieved an update in the past second
          recententries = ceresdb.dataentries.find(
              {'hwid' : self.hwid,
               'dsid' : dsid, 
               'time' : {"$gt" : self.now - datetime.timedelta(seconds=.1)} }).count()
          if recententries > 0:
            raise ProtocolException(reason='Data too new for dsid [' + str(dsid) + ']', fatal=False)

          # Insert the new data point into the database
          entry = {'hwid' : self.hwid,
                   'dsid' : dsid,
                   'time' : datetime.datetime.utcnow(),
                   'data' : data}
          ceresdb.dataentries.save(entry)

          # Remove any items that are older than 1 minute
          ceresdb.dataentries.remove(
              {'hwid' : self.hwid,
               'dsid' : dsid, 
               'time' : {"$lt" : self.now - datetime.timedelta(minutes=1)} })

      else:
        raise Exception(reason='Invalid Data - too many fields [' + data + ']', fatal=False)

    except ProtocolException as e:
      log.msg(str(self.transport.getHost()) + ' Exception: ' + e.reason)
      if e.fatal:
        self.transport.loseConnection()

log.startLogging(open('/var/log/ceres.log', 'w'))

dbconnection = pymongo.Connection()
ceresdb = dbconnection.ceres

factory = Factory()
factory.protocol = DeviceProtocol
reactor.listenTCP(10000, factory, interface='192.168.1.1')
reactor.run()

