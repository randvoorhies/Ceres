# -*- coding: utf-8 -*-
from functools import wraps
import flask
import werkzeug
from flask import Flask, jsonify, render_template, request, json, session, flash, redirect, url_for, g
import pymongo
import datetime, time, calendar
import bcrypt
import re
import rrdtool
import operator
import logging.handlers

app = Flask(__name__)
app.secret_key = '\xba\xd0\x15\xaeH\xb6\x81M6\x15tb\xf1p4z_\x80\xd8\xf2\xf9\x05\xd1\x03'

loghandler = logging.handlers.RotatingFileHandler('/var/log/ceres/display.log', 'a', 524288, 10)
loghandler.setLevel(logging.INFO)
app.logger.addHandler(loghandler)


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

    if ceresdb.users.find_one({'username' : session['username']}) == None:
      return redirect(url_for('login'))

    return f(*args, **kwargs)
  return decorated_function

def utcnow():
  return int(calendar.timegm(time.gmtime()))


def rrdtoolfetch(source, filename, RRA, start, end, resolution, timezoneoffset=0):
  res = rrdtool.fetch(str(filename), RRA,
      '--start='+str(start),
      '--end='+str(end),
      '--resolution='+str(resolution))

  timestamps = res[0]
  names      = res[1]
  data       = res[2]

  # Find the requested source name
  nameidx = names.index(source);

  result = []

  for t,d in enumerate(data):
    timestamp = (timestamps[0] + t*timestamps[2]) * 1000
    result.append([timestamp + timezoneoffset, d[nameidx]])

  return result


######################################################################
# Get Data Responder 
######################################################################
@app.route('/_getdata')
@login_required
def getdata():
  hwid        = request.args.get('hwid',       default='')
  source      = request.args.get('source',     default='')
  start       = int(request.args.get('start',  default=-60))
  end         = request.args.get('end',        default='N')
  resolution  = request.args.get('resolution', default='1')

  device = ceresdb.devices.find_one({'hwid' : hwid})
  if device['username'] != session['username']:
    flash('Wrong username [' + session['username'] + '] for device [' + hwid + ']')
    return redirect(url_for('myceres'))

  # Get the user's timezone
  userinfo = ceresdb.users.find_one({'username' : session['username']})
  timezone = float(userinfo['settings']['timezone'])
  timezoneoffset = timezone * 60 * 60 * 1000
  
  now = utcnow()

  if start < 0:
    start = now + start
  else:
    start = start - timezoneoffset/1000
  start = str(int(start))

  if end == 'N':
    end = now
  else:
    end = end - timezoneoffset/1000
  end = str(int(end))

  avgresult = rrdtoolfetch(source, device['file'], 'AVERAGE', start, end, resolution, timezoneoffset)
  minresult = []
  maxresult = []
  if resolution > 1:
    minresult = rrdtoolfetch(source, device['file'], 'MIN', start, end, resolution, timezoneoffset)
    maxresult = rrdtoolfetch(source, device['file'], 'MAX', start, end, resolution, timezoneoffset)

  return jsonify(data={'avg' : avgresult,
                       'min' : minresult,
                       'max' : maxresult} )

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
            'min' : str(avgmin)[0:5],
            'avg' : str(avgvals[2][0][idx])[0:5],
            'max' : str(avgmax)[0:5]}

    else:
      statii[hwid]['msg'] = "No report recieved for {0} seconds".format(now-timestamp)

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

  RRAs = []
  # Extract the info about the RRAs
  r = re.compile('rra\[(.*)\]\.cf')
  for RRAid in sorted([int(match.group(1)) for match in [r.match(key) for key in info if r.match(key)]]):
    rra = 'rra['+str(RRAid)+']'

    if info[rra + '.cf'] != 'AVERAGE':
      continue

    RRAs.append({
        'resolution' : info[rra + '.pdp_per_row'] * step,
        'totaltime'  : info[rra + '.pdp_per_row'] * step * info[rra + '.rows']
    })

  RRAs = sorted(RRAs, key=lambda k: k['resolution'])
  return jsonify(data={'RRAs' : RRAs, 'sources' : sourcenames})

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
# Settings Page
######################################################################
@app.route('/settings/')
@login_required
def settings(username=None):
  username = session['username']
  user = ceresdb.users.find_one({'username' : username})

  settings = {'bad' : 'value'}
  if "settings" in user: settings = user['settings']

  return render_template('settings.html', username=username, settings=settings)

######################################################################
# Save Settings Responder
######################################################################
@app.route('/_savesettings', methods=['POST'])
@login_required
def savesettings(username=None):
  username = session['username']

  timezone = request.form['timezone']

  ceresdb.users.update({'username' : username},
      {
        "$set" :
          {"settings" :
            {
              "timezone" : timezone
            }
          }
      })
  flash('Settings Saved')

  return redirect(url_for('settings'))

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
