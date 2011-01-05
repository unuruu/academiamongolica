# -*- coding: utf-8 -*-
from google.appengine.ext import db

class OAuthToken(db.Model):
    token_key = db.StringProperty(required=True)
    token_secret = db.StringProperty(required=True)

class Entry(db.Model):
    entry = db.StringProperty(required=True)
    description = db.StringProperty()
    user = db.StringProperty(required=True)
    when = db.DateTimeProperty(auto_now=True, auto_now_add=True)

class Translation(db.Model):
    entry = db.ReferenceProperty(Entry)
    translation = db.StringProperty(required=True)
    vote = db.IntegerProperty(default=0)
    user = db.StringProperty(required=True)
    when = db.DateTimeProperty(auto_now=True, auto_now_add=True)
    
class Vote(db.Model):
    translation = db.ReferenceProperty(Translation)
    type = db.IntegerProperty(required=True)
    user = db.StringProperty(required=True)
    when = db.DateTimeProperty(auto_now=True, auto_now_add=True)

class Comment(db.Model):
    translation = db.ReferenceProperty(Translation)
    comment = db.StringProperty(required=True)
    user = db.StringProperty(required=True)
    when = db.DateTimeProperty(auto_now=True, auto_now_add=True)
