# -*- coding: utf-8 -*-

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from gaesessions import get_current_session

import simplejson
import urllib
import datetime
import tweepy
import models

consumer_token = "Q8XwfqvIapJ4TmcxCDwTGg"
consumer_secret = "w3py8vuCoYqv0fwrX4Xf25YOw7Z8JxQGj63b5Uv78"

class TwitterAuthPage(webapp.RequestHandler):
    def get(self):
        auth = tweepy.OAuthHandler(consumer_token, consumer_secret, "http://localhost:9999/twitter_back")
        url = auth.get_authorization_url()
        models.OAuthToken(
            token_key = auth.request_token.key,
            token_secret = auth.request_token.secret
        ).put()
        self.redirect(url)

class TwitterOutPage(webapp.RequestHandler):
    def get(self):
        session = get_current_session()
        session.terminate()
        self.redirect("/")

class TwitterBackPage(webapp.RequestHandler):
    def get(self):
        oauth_token = self.request.get("oauth_token", None)
        oauth_verifier = self.request.get("oauth_verifier", None)
        request_token = models. OAuthToken.gql("WHERE token_key=:key", key=oauth_token).get()
        if request_token is None:
            print "Invalid token"
            return
        auth = tweepy.OAuthHandler(consumer_token, consumer_secret)
        auth.set_request_token(request_token.token_key, request_token.token_secret)
        auth.get_access_token(oauth_verifier)
        api = tweepy.API(auth)
        session = get_current_session()
        session["twitter_user"] = api.me().screen_name
        self.redirect("/")

class LastEntryPage(webapp.RequestHandler):
    def get(self):
        entry = models.Entry.gql("order by when desc").get()
        self.redirect("/" + str(entry.key().id()))

class LookupPage(webapp.RequestHandler):
    def get(self):
        query = self.request.get("query")
        entries = models.Entry.gql("where entry>=:1 and entry<:2", query, query + u'\ufffd')
        json = "{\"query\": \"" + query + "\", \"suggestions\": ["
        for entry in entries:
            json += "\"" + entry.entry + "\","
        json += "]}"
        self.response.out.write(json)

class NewEntryPage(webapp.RequestHandler):
    def post(self):
        session = get_current_session()
        if session.has_key("twitter_user"):
            entry = models.Entry(
                entry = self.request.get("entry").lower(),
                description = self.request.get("description").replace("\n", " "),
                user = session["twitter_user"]
                )
            entry.put()
            self.redirect("/" + str(entry.key().id()))
        else:
            self.redirect("/")
        
class NewTranslationPage(webapp.RequestHandler):
    def post(self):
        session = get_current_session()
        entry = models.Entry.gql("where __key__=Key('Entry', :1)", 
                    int(self.request.get("entry"))).get()
        if session.has_key("twitter_user"):
            models.Translation(
                entry = entry,
                translation = self.request.get("translation").replace("\n", " "),
                user = session["twitter_user"]
                ).put()
            self.redirect("/" + str(entry.key().id()))
        else:
            self.redirect("/")

class EntryPage(webapp.RequestHandler):
    def post(self, entryid):
        session = get_current_session()
        word = self.request.get("lookup")
        entry = models.Entry.gql("where entry=:1", word.lower()).get()
        template_values = {}
        
        new_entries = models.Entry.gql("order by when desc").fetch(20)
        template_values["new_entries"] = new_entries
        
        if entry is None:
            entry =  models.Entry(
                entry = urllib.unquote(word).lower(), 
                description = "Ийм үг байхгүй байна",
                user = "dagvadorj")
        else:
            translations = models.Translation.gql("where entry=:1 order by vote desc", entry)
            template_values["translations"] = translations
        template_values["entry"] = entry
        if session.has_key("twitter_user"):
            template_values["user"] = session["twitter_user"]
        self.response.out.write(template.render("index.html", template_values))
    def get(self, entryid):
        session = get_current_session()
        entry = models.Entry.gql("where __key__=Key('Entry',:1)", int(entryid)).get()
        template_values = {}
        
        new_entries = models.Entry.gql("order by when desc").fetch(20)
        template_values["new_entries"] = new_entries
        
        if entry is None:
            self.redirect("/")
            return
        else:
            translations = models.Translation.gql("where entry=:1 order by vote desc", entry)
            template_values["translations"] = translations
        template_values["entry"] = entry
        if session.has_key("twitter_user"):
            template_values["user"] = session["twitter_user"]
        self.response.out.write(template.render("index.html", template_values))

class VotePage(webapp.RequestHandler):
    def post(self):
        session = get_current_session()
        if session.has_key("twitter_user"):
            trans = self.request.get("translation")
            val = int(self.request.get("val"))
            translation = models.Translation.gql("where __key__ = Key('Translation',:1)", int(trans)).get()
            votes = models.Vote.gql("where translation=:1 and user=:2", translation, session["twitter_user"])
            if votes.count() == 0:
                vote = models.Vote(user = session["twitter_user"])
                vote.translation = translation
                vote.type = val
                vote.put()
                translation.vote += val
                translation.put()
            else:
                vote = votes[0]
                if val == vote.type:
                    self.response.out.write("DUPLICATE")
                    return
                else:
                    vote.type = val
                    vote.put()
                    translation.vote += 2*val
                    translation.put()
            self.response.out.write(
                "{\"translation\": " + trans + ", " + 
                " \"vote\": \"" + str(translation.vote) + "\"}")
        else:
            self.response.out.write("NOTLOGGEDIN")

class CommentPage(webapp.RequestHandler):
    def get(self, translation_key):
        translation = models.Translation.gql("where __key__ = Key('Translation',:1)", 
            int(translation_key))[0]
        comments = models.Comment.gql("where translation=:1 order by when desc", translation)
        template_values = {
            "translation": translation,
            "comments": comments
            }
        session = get_current_session()
        if session.has_key("twitter_user"):
            template_values["user"] = session["twitter_user"]
        self.response.out.write(template.render("comments.html", template_values))
    def post(self, translation_key):
        session = get_current_session()
        if session.has_key("twitter_user"):
            translation = models.Translation.gql("where __key__ = Key('Translation',:1)", 
                int(translation_key))[0]
            comment = self.request.get("comment").replace("\n", " ")
            new_comment = models.Comment(user=session["twitter_user"], 
                comment = comment, translation = translation)
            new_comment.put()
        self.redirect("/comments/" + translation_key)
        
class SetDatePage(webapp.RequestHandler):
    def get(self):
        now = datetime.datetime.now()
        for translation in models.Translation.all():
            translation.when = now
            translation.put()
        for entry in models.Entry.all():
            entry.when = now
            entry.put()
        for comment in models.Comment.all():
            comment.when = now
            comment.put()
        for vote in models.Vote.all():
            vote.when = now
            vote.put()

application = webapp.WSGIApplication([
				    ('/', LastEntryPage),
				    ('/lookup', LookupPage),
				    ('/new_entry', NewEntryPage),
				    ('/new_translation', NewTranslationPage),
				    ('/vote', VotePage),
				    ('/comments/([0-9]+)', CommentPage),
				    ('/twitter_auth', TwitterAuthPage),
				    ('/twitter_back', TwitterBackPage),
				    ('/twitter_out', TwitterOutPage),
				    ('/set_date', SetDatePage),
				    ('/([0-9]+)', EntryPage)],
				    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    if models.Entry.all().count() == 0:
        models.Entry(
            entry = "mongolia",
            description = "The country we love!",
            user = "dagvadorj"
        ).put()
    main()
