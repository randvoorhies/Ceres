#!/usr/bin/env python
import pymongo
import os
import time, datetime, calendar

ceresdb = pymongo.Connection().ceres

username = raw_input('Username: ')
if ceresdb.users.find({'username' : username}).count() == 0:
  print 'Invalid username! Nothing removed'
  exit(-1)

user = ceresdb.users.find_one({'username' : username})

hwid = raw_input('HWID: ')

device = ceresdb.devices.find_one({'hwid' : hwid})

if device == None:
  print 'Invalid hwid'
  exit(-1)

if device['username'] != username:
  print 'That hwid does not belong to the user ['+username+']. It actually belongs to ['+device['username']+']'
  exit(-1)

os.remove(device['file'])
print 'File Removed'

ceresdb.devices.remove(device)
print 'Database Entry Removed'
