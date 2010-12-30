# -*- coding: utf-8 -*-
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from gaesessions import get_current_session
from django.utils import simplejson

import urllib

import models

def uhref(entry):
    return """
        <html>
            <head>
                <script type="text/javascript">
                    location.href=\"/""" + entry + """\";
                </script>
            </head>
        </html>
    """

class RandomPage(webapp.RequestHandler):
    def get(self):
        entries = models.Entry.gql("order by __key__ desc")
        self.response.out.write(uhref(entries[0].entry))
        # self.redirect("/" + entries[0].entry)

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
        new_entry = self.request.get("entry")
        new_description = self.request.get("description").replace("\n", " ")
        models.Entry(
            entry = new_entry,
            description = new_description).put()
        # self.response.headers['Location'] = urllib.quote("ыбөы".encode('utf-8'))
        # self.redirect(urllib.quote("/" + new_entry.decode("utf-8")))
        self.response.out.write(uhref(new_entry))

class NewTranslationPage(webapp.RequestHandler):
    def post(self):
        new_entry = self.request.get("entry")
        new_translation = self.request.get("translation").replace("\n", " ")
        models.Translation(
            entry = models.Entry.gql("where entry=:1", new_entry)[0],
            translation = new_translation).put()
        self.redirect("/" + new_entry)

class VotePage(webapp.RequestHandler):
    def post(self):
        trans = self.request.get("translation")
        val = self.request.get("val")
        translation = models.Translation.gql("where __key__ = Key('Translation',:1)", int(trans))[0]
        if val == "up":
            translation.vote += 1
        else:
            translation.vote -= 1
        translation.put()
        self.response.out.write("{\"translation\": " + trans + ", \"vote\": \"" + str(translation.vote) + "\"}")

class EntryPage(webapp.RequestHandler):
    def get(self, entry):
        # print urllib.quote(entry).encode('utf-8')
        entries = models.Entry.gql("where entry=:1", urllib.quote(entry).encode('utf-8'))
        if entries.count() == 0:
            template_values = {
                "entry": models.Entry(entry=urllib.unquote(entry), description="Ийм үг байхгүй байна"),
                "entry_exists": 0
                }
            self.response.out.write(template.render("index.html", template_values))
        else:
            translations = models.Translation.gql("where entry=:1 order by vote desc", entries[0])
            template_values = {
                    "entry": entries[0],
                    "entry_exists": 1,
                    "translations": translations,
                    "translations_count": translations.count()
                    }        
            self.response.out.write(template.render("index.html", template_values))

application = webapp.WSGIApplication([
				    ('/', RandomPage),
				    ('/lookup', LookupPage),
				    ('/new', NewPage),
				    ('/new_translation', NewTranslationPage),
				    ('/vote', VotePage),
				    ('/(.*)', EntryPage)],
				    debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    if models.Entry.all().count() == 0:
        models.Entry(
            entry = "Mongolia",
            description = "The country we love!"
        ).put()
    main()
