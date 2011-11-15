# -*- coding: utf-8 -*-

from flask import Flask, jsonify, render_template, request
import pymongo

app = Flask(__name__)

@app.route('/_getdata')
def getdata():
  global ceresdb
  hwid = request.args.get('hwid')

  result = ''
  for entry in ceresdb.dataentries.find({'hwid' : hwid}).sort('time',1):
    result += str(entry['time']) + ' - ' + str(entry['data']) + '<br>'
  return jsonify(result=result)

@app.route('/')
@app.route('/<hwid>')
def index(hwid=None):
  if hwid == None:
    return 'Give me a device id!'
  else:
    deviceinfo = ceresdb.devices.find_one({'hwid' : hwid})
    if deviceinfo == None:
      alldevices = "<h1>All Devices:</h1>"
      for device in ceresdb.devices.find():
        alldevices += 'Device: ' + device['hwid'] + '<br>'
      return alldevices

    else:
      return render_template('index.html', hwid=hwid)

ceresdb = None
if __name__ == '__main__':
  global ceresdb

  dbconnection = pymongo.Connection()
  ceresdb = dbconnection.ceres
  app.run(debug=True)

