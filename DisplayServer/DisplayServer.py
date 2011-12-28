# -*- coding: utf-8 -*-
from functools import wraps
from flask import Flask, jsonify, render_template, request, json, session, flash, redirect, url_for, g
import pymongo
import datetime, time, calendar
import bcrypt
import re
import rrdtool
import operator

app = Flask(__name__)
app.secret_key = '\xba\xd0\x15\xaeH\xb6\x81M6\x15tb\xf1p4z_\x80\xd8\xf2\xf9\x05\xd1\x03'
try:
  dbconnection = pymongo.Connection()
except pymongo.errors.AutoReconnect:
  print 'Can not connect to MongoDB server!'
  exit(-1)
ceresdb = dbconnection.ceres

def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if not 'username' in session:
      return redirect(url_for('login'))
    return f(*args, **kwargs)
  return decorated_function

def utcnow():
  return int(calendar.timegm(time.gmtime()))

######################################################################
# Get Data Responder 
######################################################################
@app.route('/_getdata')
@login_required
def getdata():
  hwid        = request.args.get('hwid')
  start       = request.args.get('start')
  end         = request.args.get('end')
  resolution  = request.args.get('resolution')

  if end == 'N': end = str(utcnow())

  device = ceresdb.devices.find_one({'hwid' : hwid})
  if device['username'] != session['username']:
    flash('Wrong username [' + session['username'] + '] for device [' + hwid + ']')
    return redirect(url_for('myceres'))

  try:
    now = utcnow()
    res = rrdtool.fetch(str(device['file']), 'AVERAGE',
        '--start='+str(now-60),
        '--start='+start,
        '--end='+end)

    timestamps = res[0]
    names      = res[1]
    data       = res[2]

    result = {}
    result['datastreams'] = {}
    resdata = []

    for n in names:
      resdata.append([])

    for t,d in enumerate(data):
      timestamp = (timestamps[0] + t*timestamps[2]) * 1000
      for i, p in enumerate(d):
        resdata[i].append((timestamp,p))

    for i,d in enumerate(resdata):
      result['datastreams'][names[i]] = d

    return jsonify(data=result)
  except rrdtool.error as e:
    print ' Oh crap...' + e.str()
  return ''

######################################################################
# Get Status Responder
######################################################################
@app.route('/_getstatus')
@login_required
def getstatus():
  hwids = request.args.get('hwids').split(',')
  hwids = map(lambda x: str(x), hwids)

  now = utcnow()
  statii = {}
  for hwid in hwids:
    if hwid == '': continue

    statii[hwid] = {}
    statii[hwid]['time'] = -1
    statii[hwid]['online']   = False
    statii[hwid]['msg']  = ""
    statii[hwid]['values'] = {}

    device = ceresdb.devices.find_one({'hwid' : hwid})

    if device == None: continue

    if device['username'] != session['username']:
      flash('Wrong username [' + session['username'] + '] for device [' + hwid + ']')
      return redirect(url_for('myceres'))

    try:
      timestamp = rrdtool.last(str(device['file']))

      statii[hwid]['time'] = now-timestamp
      if (now - timestamp) < 5:
        statii[hwid]['online'] = True

        minvals = rrdtool.fetch(str(device['file']), 'MIN',     '--start='+str(timestamp-3600), '--end='+str(timestamp))
        avgvals = rrdtool.fetch(str(device['file']), 'AVERAGE', '--start='+str(timestamp-1),    '--end='+str(timestamp))
        maxvals = rrdtool.fetch(str(device['file']), 'MAX',     '--start='+str(timestamp-3600), '--end='+str(timestamp))

        for idx, sensorname in enumerate(avgvals[1]):
          avgmin=0
          n = 0
          for minval in minvals[2]:
            if minval[idx] != None:
              avgmin += minval[idx]
              n += 1
          if n > 0:
            avgmin /= float(n)

          avgmax=0
          n = 0
          for maxval in maxvals[2]:
            if maxval[idx] != None:
              avgmax += maxval[idx]
              n += 1
          if n > 0:
            avgmax /= float(n)

          statii[hwid]['values'][sensorname] = {
              'min' : str(avgmin)[0:4],
              'avg' : avgvals[2][0][idx],
              'max' : str(avgmax)[0:4]}

      else:
        statii[hwid]['msg'] = "No report recieved for {0} seconds".format(now-timestamp)
    except rrdtool.error as e:
      statii[hwid]['msg'] = "Error retrieving RRD file. Please file a bug report!"

  return jsonify(data=statii)
    
######################################################################
# List Sources Responder
######################################################################
@app.route('/_listSources')
@login_required
def listSources():
  hwid = request.args.get('hwid')
  device = ceresdb.devices.find_one({'hwid' : hwid})
  if device['username'] != session['username']:
    flash('Wrong username [' + session['username'] + '] for device [' + hwid + ']')
    return redirect(url_for('myceres'))

  info = rrdtool.info(str(device['file']))
  step = int(info['step'])

  # Pull out all of the source names (e.g. temperature, light, etc..)
  r = re.compile('ds\[(.*)\]\.type')
  sourcenames = [match.group(1) for match in [r.match(key) for key in info if r.match(key)]]
  print sourcenames

  RRAs = []
  # Extract the info about the RRAs
  r = re.compile('rra\[(.*)\]\.cf')
  for RRAid in sorted([int(match.group(1)) for match in [r.match(key) for key in info if r.match(key)]]):
    rra = 'rra['+str(RRAid)+']'

    if info[rra + '.cf'] != 'AVERAGE':
      continue

    print 'GOT RRA'

    RRAs.append({
        'resolution' : info[rra + '.pdp_per_row'] * step,
        'totaltime'  : info[rra + '.pdp_per_row'] * step * info[rra + '.rows']
    })

  RRAs = sorted(RRAs, key=lambda k: k['resolution'])
  return jsonify(data={'RRAs' : RRAs, 'sources' : sourcenames})


######################################################################
# Update Sources Responder
######################################################################
@app.route('/_updateSources')
@login_required
def updateSources():
  hwid           = request.args.get('hwid')
  #starttimestamp = request.args.get('starttimestamp')
  #endtimestamp   = request.args.get('endtimestamp')

  device = ceresdb.devices.find_one({'hwid' : hwid})
  if device['username'] != session['username']:
    flash('Wrong username [' + session['username'] + '] for device [' + hwid + ']')
    return redirect(url_for('myceres'))

  try:
    now = utcnow()
    res = rrdtool.fetch(str(device['file']), 'AVERAGE',
        '--start='+str(now-60),
        '--end='+str(now))

    timestamps = res[0]
    names      = res[1]
    data       = res[2]

    result = {}
    result['datastreams'] = {}
    resdata = []

    for n in names:
      resdata.append([])

    for t,d in enumerate(data):
      timestamp = (timestamps[0] + t*timestamps[2]) * 1000
      for i, p in enumerate(d):
        resdata[i].append((timestamp,p))

    for i,d in enumerate(resdata):
      result['datastreams'][names[i]] = d

    return jsonify(data=result)
  except rrdtool.error as e:
    print ' Oh crap...' + e.str()
  return ''


######################################################################
# Login Page
######################################################################
@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':

    username = request.form['username']
    password = request.form['password']

    userinfo = ceresdb.users.find_one({'username' : username})

    if userinfo == None:
      flash('Invalid Username/Password')
      return render_template('login.html', username=None)

    hashedpassword = bcrypt.hashpw(password, userinfo['hashedpassword'])
    if hashedpassword == userinfo['hashedpassword']:
      flash('You have logged in as ' + username)
      session['username'] = username
      return redirect(url_for('myceres'))

    else:
      flash('Invalid Username/Password')
      return render_template('login.html', username=None)
  else:
    if 'username' in session:
      flash('You are already logged in!')
      return redirect(url_for('myceres'))
    else:
      return render_template('login.html', username=None)

######################################################################
# Logout Page
######################################################################
@app.route('/logout')
def logout():
  flash('You have logged out')
  session.pop('username', None)
  return redirect(url_for('index'))

######################################################################
# Homepage
######################################################################
@app.route('/')
def index(hwid=None):
  username = None
  if 'username' in session:
    username = session['username']
  return render_template('index.html', username=username)

######################################################################
# User Page
######################################################################
@app.route('/myceres/')
@login_required
def myceres(username=None):
  username = session['username']
  devices = []
  for device in ceresdb.devices.find({'username' : username}):
    devices.append(str(device['hwid']))
  return render_template('myceres.html', username=username, devices=devices)


######################################################################
# Device Page
######################################################################
@app.route('/myceres/<hwid>')
@login_required
def devices(hwid=None):
  username = session['username']
  device = ceresdb.devices.find_one({'hwid' : hwid})
  if device == None or device['username'] != username:
    flash('You do not own the requested device')
    return redirect(url_for('myceres'))

  info = rrdtool.info(str(device['file']))
  step = int(info['step'])

  # Pull out all of the source names (e.g. temperature, light, etc..)
  r = re.compile('ds\[(.*)\]\.type')
  sources = [match.group(1) for match in [r.match(key) for key in info if r.match(key)]]

  return render_template('hardwareview.html', username=username, hwid=hwid, sources=sources)

if __name__ == '__main__':

  app.run(debug=True)
