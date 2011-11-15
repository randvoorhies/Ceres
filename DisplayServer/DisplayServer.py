# -*- coding: utf-8 -*-

from flask import Flask, jsonify, render_template, request
app = Flask(__name__)

@app.route('/_getdata')
def getdata():
  hdid = request.args.get('hdid')
  return jsonify(result="You said: " + hdid)

@app.route('/')
@app.route('/<hdid>')
def index(hdid=None):
  if hdid == None:
    return 'Give me a device id!'
  else:
    return render_template('index.html', hdid=hdid)

if __name__ == '__main__':
  app.run(debug=True)

