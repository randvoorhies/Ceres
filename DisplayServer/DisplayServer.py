# -*- coding: utf-8 -*-

from flask import Flask, jsonify, render_template, request, json
import pymongo

ceresdb = None
app = Flask(__name__)

@app.route('/_getdata')
def getdata():
  global ceresdb
  hwid = request.args.get('hwid')
  print 'Getting data'

  result = []
  for entry in ceresdb.dataentries.find({'hwid' : hwid}).sort('time',1):
    result.append((str(entry['time']), str(entry['data'])))
  return jsonify(data=result)

@app.route('/')
@app.route('/mydevice/<hwid>')
def index(hwid=None):
  global ceresdb
  deviceinfo = ceresdb.devices.find_one({'hwid' : hwid})
  if deviceinfo == None:
    # If no valid HWID was given in the URL, just display them all
    alldevices = ''

    if hwid != None:
      alldevices += "<h1>Bad Device!</h1>"

    alldevices += "<h2>All Devices:</h2>"
    for device in ceresdb.devices.find():
      alldevices += 'Device: ' + device['hwid'] + '<br>'
    return alldevices

  else:
    # If a valid HWID was given, then render the data display template
    return render_template('index.html', hwid=hwid)

if __name__ == '__main__':

  dbconnection = pymongo.Connection()
  ceresdb = dbconnection.ceres
  app.run(debug=True)

