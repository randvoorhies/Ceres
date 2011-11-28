# -*- coding: utf-8 -*-
from functools import wraps
from flask import Flask, jsonify, render_template, request, json, session, flash, redirect, url_for, g
import pymongo
import datetime, time
import bcrypt
import rrdtool

ceresdb = None
app = Flask(__name__)
app.secret_key = '\xba\xd0\x15\xaeH\xb6\x81M6\x15tb\xf1p4z_\x80\xd8\xf2\xf9\x05\xd1\x03'

def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if not 'username' in session:
      return redirect(url_for('login'))
    return f(*args, **kwargs)
  return decorated_function

######################################################################
# Get Status Responder
######################################################################
@app.route('/_getstatus')
@login_required
def getstatus():
  hwids = request.args.get('hwids').split(',')
  hwids = map(lambda x: str(x), hwids)

  now = int(time.mktime(datetime.datetime.utcnow().timetuple()))
  statii = {}
  for hwid in hwids:
    if hwid == '':
      continue

    statii[hwid] = {}
    statii[hwid]['timestamp'] = -1
    statii[hwid]['ok'] = False
    statii[hwid]['msg'] = ""

    device = ceresdb.devices.find_one({'hwid' : hwid})

    if device['username'] != session['username']:
      flash('Wrong username [' + session['username'] + '] for device [' + hwid + ']')
      return redirect(url_for('myceres'))

    try:
      timestamp = rrdtool.last(str(device['file']))
      statii[hwid]['timestamp'] = timestamp
      if (now - timestamp) < 5:
        statii[hwid]['ok'] = True
      else:
        statii[hwid]['msg'] = "No report recieved for {0} seconds".format(now-timestamp)
    except rrdtool.error as e:
      statii[hwid]['msg'] = "Error retrieving RRD file. Please file a bug report!"

  return jsonify(data=statii)
    

######################################################################
# Get Data Responder
######################################################################
@app.route('/_getdata')
@login_required
def getdata():
  hwid           = request.args.get('hwid')
  #starttimestamp = request.args.get('starttimestamp')
  #endtimestamp   = request.args.get('endtimestamp')

  device = ceresdb.devices.find_one({'hwid' : hwid})
  if device['username'] != session['username']:
    flash('Wrong username [' + session['username'] + '] for device [' + hwid + ']')
    return redirect(url_for('myceres'))

  try:
    now = int(time.mktime(datetime.datetime.utcnow().timetuple()))
    print 'Fetching...' + device['file']
    res = rrdtool.fetch(str(device['file']), 'AVERAGE',
        '--start='+str(now-60),
        '--end='+str(now))
        #'--start='+starttimestamp,
        #'--end='+endtimestamp)
        
    #print 'RES: ' + str(res)

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
  error = None
  if request.method == 'POST':

    username = request.form['username']
    password = request.form['password']

    userinfo = ceresdb.users.find_one({'username' : username})

    if userinfo == None:
      return render_template('login.html', error='Invalid Username/Password', username=None)

    hashedpassword = bcrypt.hashpw(password, userinfo['hashedpassword'])
    if hashedpassword == userinfo['hashedpassword']:
      session['username'] = username

      return redirect(url_for('myceres'))

    else:
      return render_template('login.html', error='Invalid Username/Password', username=None)
  else:
    if 'username' in session:
      flash('You are already logged in!')
      return redirect(url_for('myceres'))
    else:
      return render_template('login.html', error=None, username=None)

######################################################################
# Logout Page
######################################################################
@app.route('/logout')
def logout():
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
@app.route('/myceres')
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
  deviceinfo = ceresdb.devices.find_one({'hwid' : hwid})
  if deviceinfo == None or deviceinfo['username'] != username:
    flash('You do not own the requested device')
    return redirect(url_for('myceres'))
  return render_template('hardwareview.html', username=username, hwid=hwid)

if __name__ == '__main__':

  dbconnection = pymongo.Connection()
  ceresdb = dbconnection.ceres
  app.run(debug=True)

