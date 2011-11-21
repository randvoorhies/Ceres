#!/usr/bin/env python
import pymongo

ceresdb = pymongo.Connection().ceres

for user in ceresdb.users.find().sort('username'):
  print 'User: ' + user['username']
  for device in ceresdb.devices.find({'username' : user['username']}):
    print '  Device: ' + device['hwid']

