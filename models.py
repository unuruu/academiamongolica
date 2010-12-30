# -*- coding: utf-8 -*-
from google.appengine.ext import db

class Entry(db.Model):
    entry = db.StringProperty(required=True)
    description = db.StringProperty()
    # categories = db.StringListProperty()

class Translation(db.Model):
    entry = db.ReferenceProperty(Entry)
    translation = db.StringProperty(required=True)
    vote = db.IntegerProperty(default=0)

class Comment(db.Model):
    translation = db.ReferenceProperty(Translation)
    comment = db.StringProperty()