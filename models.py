# -*- coding: utf-8 -*-
from google.appengine.ext import db

class OAuthToken(db.Model):
    token_key = db.StringProperty(required=True)
    token_secret = db.StringProperty(required=True)

class Entry(db.Model):
    entry = db.StringProperty(required=True)
    description = db.StringProperty()
    # categories = db.StringListProperty()
    user = db.StringProperty(required=True)

class Translation(db.Model):
    entry = db.ReferenceProperty(Entry)
    translation = db.StringProperty(required=True)
    vote = db.IntegerProperty(default=0)
    user = db.StringProperty(required=True)
    
class Vote(db.Model):
    translation = db.ReferenceProperty(Translation)
    type = db.IntegerProperty()
    user = db.StringProperty(required=True)

class Comment(db.Model):
    translation = db.ReferenceProperty(Translation)
    comment = db.StringProperty()
    user = db.StringProperty(required=True)
