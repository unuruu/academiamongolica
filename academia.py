# -*- coding: utf-8 -*-

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from gaesessions import get_current_session
import simplejson
import urllib
import tweepy
import models

consumer_token = "Q8XwfqvIapJ4TmcxCDwTGg"
consumer_secret = "w3py8vuCoYqv0fwrX4Xf25YOw7Z8JxQGj63b5Uv78"

class TweetAuthPage(webapp.RequestHandler):
    def get(self):
        auth = tweepy.OAuthHandler(consumer_token, consumer_secret)
        url = auth.get_authorization_url()
        models.OAuthToken(
            token_key = auth.request_token.key,
            token_secret = auth.request_token.secret
        ).put()
        self.redirect(url)

class TweetOutPage(webapp.RequestHandler):
    def get(self):
        session = get_current_session()
        session.terminate()
        self.redirect("/")

class TweetBackPage(webapp.RequestHandler):
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

class RandomPage(webapp.RequestHandler):
    def get(self):
        entries = models.Entry.gql("order by __key__ desc")
        self.redirect("/" + entries[0].entry)

class LookupPage(webapp.RequestHandler):
    def get(self):
        query = self.request.get("query")
        entries = models.Entry.gql("where entry>=:1 and entry<:2", query, query + u'\ufffd')
        ret = "{\"query\": \"" + query + "\", \"suggestions\": ["
        for entry in entries:
            ret += "\"" + entry.entry + "\","
        ret += "]}"
        self.response.out.write(ret)

class NewPage(webapp.RequestHandler):
    def post(self):
        session = get_current_session()
        if session.has_key("twitter_user"):
            new_entry = self.request.get("entry")
            new_description = self.request.get("description").replace("\n", " ")
            models.Entry(
                entry = new_entry,
                description = new_description,
                user = session["twitter_user"]
                ).put()
            self.redirect("/" + new_entry)
        else:
            self.redirect("/")
        
class NewTranslationPage(webapp.RequestHandler):
    def post(self):
        session = get_current_session()
        if session.has_key("twitter_user"):
            new_entry = self.request.get("entry")
            new_translation = self.request.get("translation").replace("\n", " ")
            models.Translation(
                entry = models.Entry.gql("where entry=:1", new_entry)[0],
                translation = new_translation,
                user = session["twitter_user"]
                ).put()
            self.redirect("/" + new_entry)
        else:
            self.redirect("/")

class VotePage(webapp.RequestHandler):
    def post(self):
        session = get_current_session()
        if session.has_key("twitter_user"):
            trans = self.request.get("translation")
            val = int(self.request.get("val"))
            translation = models.Translation.gql("where __key__ = Key('Translation',:1)", int(trans))[0]
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
        comments = models.Comment.gql("where translation=:1 order by __key__ desc", translation)
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
            new_comment = models.Comment(user=session["twitter_user"])
            new_comment.translation = translation
            new_comment.comment = comment
            new_comment.put()
        self.redirect("/comments/" + translation_key);

class EntryPage(webapp.RequestHandler):
    def get(self, entry):
        entries = models.Entry.gql("where entry=:1", entry)
        template_values = {}
        if entries.count() == 0:
            template_values = {
                "entry": models.Entry(
                    entry=urllib.unquote(entry), 
                    description="Ийм үг байхгүй байна",
                    user="dagvadorj"),
                "entry_exists": 0
                }
        else:
            translations = models.Translation.gql("where entry=:1 order by vote desc", entries[0])
            template_values = {
                "entry": entries[0],
                "entry_exists": 1,
                "translations": translations,
                "translations_count": translations.count()
                }
        session = get_current_session()
        if session.has_key("twitter_user"):
            template_values["user"] = session["twitter_user"]
        self.response.out.write(template.render("index.html", template_values))

application = webapp.WSGIApplication([
				    ('/', RandomPage),
				    ('/lookup', LookupPage),
				    ('/new', NewPage),
				    ('/new_translation', NewTranslationPage),
				    ('/vote', VotePage),
				    ('/comments/([0-9]+)', CommentPage),
				    ('/tweet_auth', TweetAuthPage),
				    ('/tweet_back', TweetBackPage),
				    ('/tweet_out', TweetOutPage),
				    ('/(.*)', EntryPage)],
				    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    if models.Entry.all().count() == 0:
        models.Entry(
            entry = "Mongolia",
            description = "The country we love!",
            user = "dagvadorj"
        ).put()
    main()
