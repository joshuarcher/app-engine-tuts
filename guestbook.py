import os
import cgi
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
  loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
  extensions=['jinja2.ext.autoescape'],
  autoescape=True)

MAIN_PAGE_FOOTER_TEMPLATE = """\
    <form action="/sign?%s" method="post">
      <div><textarea name="content" rows="3" cols="60"></textarea></div>
      <div><input type="submit" value="Sign Guestbook"></div>
    </form>
    <hr>
    <form>Guestbook name:
      <input value="%s" name="guestbook_name">
      <input type="submit" value="switch">
    </form>
    <a href="%s">%s</a>
  </body>
</html>
"""

DEFAULT_GUESTBOOK_NAME = 'default_guestbook'

# set a parent key on the 'Greetings' to ensure they're all
# in the same entity group
def guestbook_key(guestbook_name=DEFAULT_GUESTBOOK_NAME):
  """Constructs a Datastore key for a Guestbook entity.

  We use guestbook_name as the key...
  """
  return ndb.Key('Guestbook', guestbook_name)

# [START greeting]
class Author(ndb.Model):
  """Sub model for representing an author."""
  identity = ndb.StringProperty(indexed=False)
  email = ndb.StringProperty(indexed=False)

class Greeting(ndb.Model):
  """Main model for representing an ind Guestbook entry."""
  author = ndb.StructuredProperty(Author)
  content = ndb.StringProperty(indexed=False)
  date = ndb.DateTimeProperty(auto_now_add=True)
# [END greeting]

# [START main_page]
class MainPage(webapp2.RequestHandler):
  def get(self):
    guestbook_name = self.request.get('guestbook_name', 
                                      DEFAULT_GUESTBOOK_NAME)

    # Ancestor Queries ensure the most recent greeting will be
    # retrieved in the query... Queries that span entity groups
    # are eventually consistent...?
    # [START query]
    greetings_query = Greeting.query(
      ancestor=guestbook_key(guestbook_name)).order(-Greeting.date)
    greetings = greetings_query.fetch(10)
    # [END query]

    user = users.get_current_user()
    for greeting in greetings:
      if greeting.author:
        author = greeting.author.email
        if user and user.user_id() == greeting.author.identity:
          author += ' (You)'
        self.response.write('<b>%s</b> wrote:' % author)
      else:
        self.response.write('An anonymous person wrote:')
      self.response.write('<blockquote>%s</blockquote>' % 
                          cgi.escape(greeting.content))

    if user:
      url = users.create_logout_url(self.request.uri)
      url_linktext = 'Logout'
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'

    # Write the submission form and the footer of the page...
    sign_query_params = urllib.urlencode({'guestbook_name':
                                          guestbook_name})
    self.response.write(MAIN_PAGE_FOOTER_TEMPLATE %
                        (sign_query_params, cgi.escape(guestbook_name),
                        url, url_linktext))
# [END main_page]

# [START guestbook]
class GuestBook(webapp2.RequestHandler):
  def post(self):
    # set same parent key on the 'Greeting' to ensure each
    # Greeting is in the same entity group.
    guestbook_name = self.request.get('guestbook_name',
                                      DEFAULT_GUESTBOOK_NAME)
    greeting = Greeting(parent=guestbook_key(guestbook_name))

    if users.get_current_user():
      greeting.author = Author(
              identity=users.get_current_user().user_id(),
              email=users.get_current_user().email())

    greeting.content = self.request.get('content')
    greeting.put()

    query_params = {'guestbook_name': guestbook_name}
    self.redirect('/?' + urllib.urlencode(query_params))
# [END guestbook]

app = webapp2.WSGIApplication([
  ('/', MainPage),
  ('/sign', GuestBook),
], debug=True)