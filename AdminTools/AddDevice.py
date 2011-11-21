#!/usr/bin/env python
import pymongo
import rrdtool
import os

ceresdb = pymongo.Connection().ceres

username = raw_input('Username: ')
if ceresdb.users.find({'username' : username}).count() == 0:
  print 'Invalid username'
  exit(-1)

user = ceresdb.users.find_one({'username' : username})

hwid = raw_input('HWID: ')

if ceresdb.devices.find({'hwid' : hwid}).count() != 0:
  print 'Invalid hwid - already exists!'
  exit(-1)

systemrrdpath = ceresdb.config.find_one({'key' : 'rrdpath'})['value']

rrdpath = os.path.join(systemrrdpath, user['username'])
if not os.path.exists(rrdpath):
  os.mkdir(rrdpath)
rrdfilename = os.path.join(rrdpath, hwid + '.rrd')
print 'Creating file: ' + rrdfilename

ret = rrdtool.create(
    str(rrdfilename), '--step', '60', '--start', 'N',
    'DS:temperature:GAUGE:120:U:U',
    'DS:humidity:GAUGE:120:U:U',
    'DS:light:GAUGE:120:U:U',
    'RRA:AVERAGE:0.5:1:60',      # AVG: 1-minute resolution for an hour
    'RRA:AVERAGE:0.5:10:1008',   # AVG: 10-minute resolution for a week
    'RRA:AVERAGE:0.5:60:8766',   # AVG: 1-hour resolution for a year
    'RRA:MIN:0.5:1:60',          # MIN: 1-minute resolution for an hour
    'RRA:MIN:0.5:10:1008',       # MIN: 10-minute resolution for a week
    'RRA:MIN:0.5:60:8766',       # MIN: 1-hour resolution for a year
    'RRA:MAX:0.5:1:60',          # MAX: 1-minute resolution for an hour
    'RRA:MAX:0.5:10:1008',       # MAX: 10-minute resolution for a week
    'RRA:MAX:0.5:60:8766'        # MAX: 1-hour resolution for a year
    )

ceresdb.devices.save({
  'username' : user['username'],
  'hwid'     : hwid,
  'file'     : rrdfilename})



