# -*- coding: utf-8 -*-

from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from gaesessions import get_current_session

import simplejson
import urllib
import datetime
import tweepy
import feedparser
import models

# Twitter OAuth
consumer_token = "vx4slYgEviwClevmUeKDg"
consumer_secret = "4L2wX8iChiokkF9rlDcYHsvBMI5eSHhBU2vuVI8Hk"

# bit.ly URL shortener
bitly_login = "dagvadorj"
bitly_api_key = "R_23c05ef1d017bf0e563097baf51134fc"

class BitLy():
    def __init__(self, login, apikey):
        self.login = login
        self.apikey = apikey

    def shorten(self, param):
        # url = "http://" + param
        request = "http://api.bit.ly/shorten?version=2.0.1&longUrl="
        request += param
        request += "&login=" + self.login + "&apiKey=" +self.apikey

        result = urlfetch.fetch(request)
        json = simplejson.loads(result.content)
        return json

def shorten_url(url):
    bitly = BitLy(bitly_login, bitly_api_key)
    return bitly.shorten(url)['results'][url]['shortUrl']

class TwitterAuthPage(webapp.RequestHandler):
    def get(self):
        auth = tweepy.OAuthHandler(consumer_token, consumer_secret, 
            "http://academiamongolica.appspot.com/twitter_back")
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
        session["twitter_token_key"] = auth.access_token.key
        session["twitter_token_secret"] = auth.access_token.secret
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

class AllEntriesPage(webapp.RequestHandler):
    def get(self):
        entries = models.Entry.gql("order by entry")
        template_values = {
            "entries": entries
            }        
        self.response.out.write(template.render("all_entries.html", template_values))
        
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
        if session.has_key("twitter_user") and session.has_key("twitter_token_key") and session.has_key("twitter_token_secret"):
            models.Translation(
                entry = entry,
                translation = self.request.get("translation").replace("\n", " "),
                user = session["twitter_user"]
                ).put()
            if self.request.get("tweet").lower() in ['true', 'yes', 't', '1', 'on', 'checked']:
                auth = tweepy.OAuthHandler(consumer_token, consumer_secret)
                auth.set_access_token(session["twitter_token_key"], session["twitter_token_secret"])
                api = tweepy.API(auth)
                tweet = entry.entry + " - " + self.request.get("translation").replace("\n", " ")
                tweet = tweet[0:110] + "... "
                short_url = shorten_url("http://academiamongolica.appspot.com/" + str(self.request.get("entry")))
                tweet += short_url
                api.update_status(tweet)
            self.redirect("/" + str(entry.key().id()))
        else:
            self.redirect("/")

class EntryPage(webapp.RequestHandler):
    def post(self, entryid):
        session = get_current_session()
        word = self.request.get("lookup")
        entry = models.Entry.gql("where entry=:1", word.lower()).get()
        template_values = {}
        
        new_entries = models.Entry.gql("order by when desc").fetch(10)
        template_values["new_entries"] = new_entries
        
        if entry is None:
            if word == "":
                self.redirect("/")
                return
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
        
        # blog posts        
        atomxml = feedparser.parse("http://academiamongolica.blogspot.com/feeds/posts/default")
        posts = atomxml['entries']
        template_values["blog_posts"] = posts
        
        self.response.out.write(template.render("index.html", template_values))
    def get(self, entryid):
        session = get_current_session()
        entry = models.Entry.gql("where __key__=Key('Entry',:1)", int(entryid)).get()
        template_values = {}
        
        new_entries = models.Entry.gql("order by when desc").fetch(10)
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
        
        # blog posts        
        atomxml = feedparser.parse("http://academiamongolica.blogspot.com/feeds/posts/default")
        posts = atomxml['entries']
        template_values["blog_posts"] = posts
        
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
                vote = models.Vote(user = session["twitter_user"],
                    type = val, translation = translation)
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

application = webapp.WSGIApplication([
				    ('/', LastEntryPage),
				    ('/lookup', LookupPage),
                    ('/all', AllEntriesPage),
				    ('/new_entry', NewEntryPage),
				    ('/new_translation', NewTranslationPage),
				    ('/vote', VotePage),
				    ('/comments/([0-9]+)', CommentPage),
				    ('/twitter_auth', TwitterAuthPage),
				    ('/twitter_back', TwitterBackPage),
				    ('/twitter_out', TwitterOutPage),
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
