#!/usr/bin/env python
import pymongo
import rrdtool
import os
import time
import datetime

ceresdb = pymongo.Connection().ceres

username = raw_input('Username: ')
if ceresdb.users.find({'username' : username}).count() == 0:
  print 'Invalid username! Database entry not created'
  exit(-1)

user = ceresdb.users.find_one({'username' : username})

hwid = raw_input('HWID: ')

#if ceresdb.devices.find({'hwid' : hwid}).count() != 0:
#  print 'Invalid hwid - already exists! Database entry not created'
#  exit(-1)

systemrrdpath = ceresdb.config.find_one({'key' : 'rrdpath'})['value']

rrdpath = os.path.join(systemrrdpath, user['username'])
if not os.path.exists(rrdpath):
  os.mkdir(rrdpath)
rrdfilename = os.path.join(rrdpath, hwid + '.rrd')
print 'Creating file: ' + rrdfilename

now = str(int(time.mktime(datetime.datetime.utcnow().timetuple())))

ret = rrdtool.create(
    str(rrdfilename), '--step', '1', '--start', now, 
    'DS:temperature:GAUGE:60:U:U',
    'DS:humidity:GAUGE:60:U:U',
    'DS:light:GAUGE:60:U:U',
    'RRA:AVERAGE:0.5:1:60',      # AVG: 1-second resolution for a minute
    'RRA:AVERAGE:0.5:10:360',    # AVG: 10-second resolution for an hour
    'RRA:AVERAGE:0.5:30:2880',   # AVG: 30-second resolution for a day
    'RRA:MIN:0.5:60:60',         # MIN: 1-minute resolution for an hour
    'RRA:MIN:0.5:3600:168',      # MIN: 1-hour resolution for a week
    'RRA:MAX:0.5:60:60',         # MAX: 1-minute resolution for an hour
    'RRA:MAX:0.5:3600:168',      # MAX: 1-hour resolution for a week
    )

if ret:
  print 'Could not create RRD database file! Database entry not created'
  print rrdtool.error()
  exit(-1)

ceresdb.devices.save({
  'username' : user['username'],
  'hwid'     : hwid,
  'model'    : '0',
  'file'     : rrdfilename})

