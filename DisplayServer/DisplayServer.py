# -*- coding: utf-8 -*-
from flask import Flask, jsonify, render_template, request, json, session, flash, redirect, url_for
import pymongo
import datetime, time
import bcrypt

ceresdb = None
app = Flask(__name__)
app.secret_key = '\xba\xd0\x15\xaeH\xb6\x81M6\x15tb\xf1p4z_\x80\xd8\xf2\xf9\x05\xd1\x03'

######################################################################
# Get Data Responder
######################################################################
@app.route('/_getdata')
def getdata():
  global ceresdb
  hwid = request.args.get('hwid')

  result = []
  for entry in ceresdb.dataentries.find({'hwid' : hwid}).sort('time',1):
    result.append((time.mktime(entry['time'].timetuple()), entry['data']))
  return jsonify(data=result)

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
      return render_template('login.html', error='Unknown Username')

    hashedpassword = bcrypt.hashpw(password, userinfo['hashedpassword'])
    if hashedpassword == userinfo['hashedpassword']:
      flash('Login Successful')
      session['username'] = username
      return redirect(url_for('index'))
    else:
      return render_template('login.html', error='Invalid Password')
  else:
    return render_template('login.html', error=None)

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
  return render_template('index.html')

@app.route('/mydevice/<hwid>')
def mydevice_hwid(hwid=None):
  if not 'username' in session:
    return render_template('login.html', 'You must login before accessing hardware pages')

  username = session['username']

  deviceinfo = ceresdb.devices.find_one({'hwid' : hwid})
  if deviceinfo['username'] != username:
    return 'You do not own this device!'

  return render_template('hardwareview.html', hwid=hwid)

if __name__ == '__main__':

  dbconnection = pymongo.Connection()
  ceresdb = dbconnection.ceres
  app.run(debug=True)

