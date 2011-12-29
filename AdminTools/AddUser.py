#!/usr/bin/env python
import pymongo
import bcrypt
import getpass

ceresdb = pymongo.Connection().ceres

username = raw_input('Username: ')

if ceresdb.users.find({'username' : username}).count() != 0:
  print 'Error - username already exists'
  exit(-1)

password1  = 'a'
password2  = 'b'
while password1 != password2:
  password1  = getpass.getpass('Password: ')
  password2  = getpass.getpass('Retype Password: ')
  if password1 != password2:
    print 'Error - passwords do not match'

hashedpassword = bcrypt.hashpw(password1, bcrypt.gensalt())

ceresdb.users.save({
  'username'       : username,
  'hashedpassword' : hashedpassword,
  'settings' : 
    {
      'timezone' : -8
    }
  })
