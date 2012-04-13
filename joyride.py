# -*- coding: utf-8 -*-
__author__ = 'peter'
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import functools
import markdown
import os.path
import re
import tornado.web
import tornado.wsgi
import unicodedata
import wsgiref.handlers
import scrapemark
import datetime

from google.appengine.api import users
from models import Entry
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.api import memcache
from string import Template

page_url_template=Template('http://www.zuche.com/jsp/convenience/convenienceIndex.page?mid=81171&cid=81167&page=${page}')
host_url='http://www.zuche.com/'
HTTP_DATE_FMT = '%Y-%m-%d'

from google.appengine.ext import db

class Ride(db.Model):
    title = db.StringProperty(required=True)
    car_spec=db.StringProperty()
    inventory=db.StringProperty()
    from_city = db.StringProperty(required=True)
    to_city = db.StringProperty(required=True)
    from_shop = db.StringProperty(required=True)
    to_shop = db.StringProperty(required=True)
    days_allowed = db.IntegerProperty()
    mileages_allowed= db.IntegerProperty()
    publish_date = db.DateProperty()
    available_date = db.DateProperty()
    expire_date = db.DateProperty()
    gps=db.StringProperty()
    baby_seat=db.StringProperty()
    toll=db.StringProperty()
    listed_price=db.IntegerProperty(required=True)
    discount_price=db.IntegerProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)


def rides():
    pages=(page_url_template.substitute(page=str(i)) for i in range(1, 21,1))
    for url in pages:
        for ride in scrapemark.scrape("""
        <ul class="contnwlst">
        {*
            <li>
                <div>
                    <a href="{{ [rides].url }}">{{ [rides].title }}</a>
                </div>
                <span class="floatrgt">{{ [rides].publish_date }}</span>
            </li>
        </ul>
        *}
        """, url=url)['rides']:
            yield ride

def scout():
    for ride in ({'url':host_url+ride['url'], 'title':ride['title'], 'publish_date':ride['publish_date']} for ride in rides()):
        deferred.defer(process, ride)
    
def process(ride):
    proposition=scrapemark.scrape("""
        <div class="sfc_news_txt">
            <a>{{ ride.from_shop}}</a>
            <a>{{ ride.to_shop}}</a>
            2、指定车型：<span id="modeName1">{{ ride.car_spec }}</span>   {{ ride.inventory }}
            3、可租区间： {{ ride.available_date }}至 {{ ride.expire_date }}；
        </div>
        <table class="sfc_tab">
          <tr class="sfc_news_text">
            <td>{{ ride.from_city }}—{{ ride.to_city }}</td>
            <td>{{ ride.days_allowed|int }}天</td>
            <td>{{ ride.mileages_allowed|int }}公里</td>
            <td>{{ ride.gps }}</td>
            <td>{{ ride.baby_seat }}</td>
            <td>{{ ride.listed_price|int }}元</td>
            <td>{{ ride.discount_price|int }}元</td>
            <td>{{ ride.toll }}</td>
          </tr>
        </table>
        """, url=ride['url'])['ride']
    Ride.get_or_insert(key_name=ride['url'],
              title=ride['title'],
              car_spec=proposition['car_spec'],
              inventory=proposition['inventory'],
              from_city = proposition['from_city'],
              to_city = proposition['to_city'],
              from_shop = proposition['from_shop'],
              to_shop = proposition['to_shop'],
              days_allowed = proposition['days_allowed'],
              mileages_allowed= proposition['mileages_allowed'],
              publish_date = datetime.datetime.strptime(ride['publish_date'], HTTP_DATE_FMT).date(),
              available_date = datetime.datetime.strptime(proposition['available_date'], HTTP_DATE_FMT).date(),
              expire_date = datetime.datetime.strptime(proposition['expire_date'], HTTP_DATE_FMT).date(),
              gps=proposition['gps'],
              baby_seat=proposition['baby_seat'],
              toll=proposition['toll'],
              listed_price=proposition['listed_price'],
              discount_price=proposition['discount_price'])

class BaseHandler(tornado.web.RequestHandler):
    """Implements Google Accounts authentication methods."""
    def get_current_user(self):
        user = users.get_current_user()
        if user: user.administrator = users.is_current_user_admin()
        return user

    def get_login_url(self):
        return users.create_login_url(self.request.uri)

    def render_string(self, template_name, **kwargs):
        # Let the templates access the users module to generate login URLs
        return tornado.web.RequestHandler.render_string(
            self, template_name, users=users, **kwargs)

class RidesHandler(BaseHandler):
    def get(self):
        dict=memcache.get('rides')
        if not dict:
            rides = Ride.gql("WHERE expire_date> :1 ORDER BY expire_date ASC, created DESC LIMIT 200", datetime.datetime.now())
            if not rides:
                self.write({})
                return
            dict={'rides':[]}
            for ride in rides:
                dict['rides'].append({
                'url' : ride.key().name(),
                'title' : ride.title,
                'car_spec' : ride.car_spec,
                'inventory' : ride.inventory,
                'from_city ' : ride.from_city,
                'to_city' : ride.to_city,
                'from_shop' : ride.from_shop,
                'to_shop' : ride.to_shop,
                'days_allowed' : ride.days_allowed,
                'mileages_allowed' : ride.mileages_allowed,
                'publish_date ' : ride.publish_date.isoformat(),
                'available_date ' : ride.available_date.isoformat(),
                'expire_date' : ride.expire_date.isoformat(),
                'gps' : ride.gps,
                'baby_seat' : ride.baby_seat,
                'toll' : ride.toll,
                'listed_price' : ride.listed_price,
                'discount_price' : ride.discount_price
                })
            memcache.set('rides', dict)
        self.write(dict)

def administrator(method):
    """Decorate with this method to restrict to site admins."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            if self.request.method == "GET":
                self.redirect(self.get_login_url())
                return
            raise tornado.web.HTTPError(403)
        elif not self.current_user.administrator:
            if self.request.method == "GET":
                self.redirect("/")
                return
            raise tornado.web.HTTPError(403)
        else:
            return method(self, *args, **kwargs)
    return wrapper

class ScoutHandler(BaseHandler):
    @administrator
    def get(self):
        scout()
        self.render("scout.html")
        memcache.delete('rides')

settings = {
    "blog_title": u"One Way Super Savings",
    "template_path": os.path.join(os.path.dirname(__file__), "templates"),
    "xsrf_cookies": True,
    "autoescape": None,
}
app = tornado.wsgi.WSGIApplication([
    (r"/joyride/rides.json", RidesHandler),
    (r"/joyride/scout", ScoutHandler),
], **settings)