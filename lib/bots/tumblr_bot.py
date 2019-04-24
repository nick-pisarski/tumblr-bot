import os
import sys
import logging

from urllib.parse import parse_qsl
from random import randrange
from datetime import datetime
from .bot_base import AbstractBotClass
from .sayings import POST_SAYINGS

import oauth2
import pytumblr

REQUEST_TOKEN_URL = "http://www.tumblr.com/oauth/request_token"
AUTHORIZATION_URL = "http://www.tumblr.com/oauth/authorize"
ACCESS_TOKEN_URL = "http://www.tumblr.com/oauth/access_token"
MAX_FOLLOW_LIMIT = 1000
REBLOG_CHECK_LIMIT = 100


class TumblrBot(AbstractBotClass):
    def __init__(self, name, config):
        super().__init__(name)
        self.has_access = True
        self.user = None
        self.blog_name = None
        self.past_posts = None

        if config is None:
            raise Exception("Configuration not given")

        self.config = config
        self.config.load()

    def authenticate(self):
        self.client = pytumblr.TumblrRestClient(
            self.config.consumer_key,
            self.config.consumer_secret,
            self.config.access_token,
            self.config.access_secret,
        )

        info = self.client.info()
        if info["user"]:
            self.user = info["user"]
            self.blog_name = self.user["blogs"][0]["name"]

        try:
            if "meta" in info:
                if info["meta"]["status"] == 401:
                    self.authenticated = False
                    self.logger.error(
                        "Authenication failed: {0}, {1}".format(
                            info["meta"]["status"], info["meta"]["msg"]
                        )
                    )
            else:
                self.authenticated = True
                self.logger.info("Successfully authenticated.")

        except Exception as ex:
            self.authenticated = False
            self.logger.error(sys.exc_info()[0])
            raise

    def get_dashboard(self, limit=REBLOG_CHECK_LIMIT):
        return self.client.dashboard(limit=limit)["posts"]

    def follow(self, post, name):
        if not post["followed"] and self.user["following"] < MAX_FOLLOW_LIMIT:
            self.client.follow("{}.tumblr.com".format(name))
            self.logger.info("Followed {0}".format(name))

    def get_past_posts(self, count=REBLOG_CHECK_LIMIT):
        if self.past_posts is None:
            my_posts = self.client.posts(self.blog_name, limit=count, offset=24)
            self.get_past_posts = [p["reblog_key"] for p in my_posts["posts"]]
        return self.get_past_posts

    def is_valid_reblog_post(self, post):
        # can be reblogged, not our post and is not in the last 50 posts
        posts = self.get_past_posts()
        been_posted = post["reblog_key"] in posts
        return (
            post["can_reblog"]
            and (post["blog_name"] != self.blog_name)
            and not been_posted
        )

    def get_reblog_post(self, posts):
        r_post = posts[randrange(0, len(posts))]
        while not self.is_valid_reblog_post(r_post):
            r_post = posts[randrange(0, len(posts))]

        # Add a random saying each reblogged post
        return r_post

    def generate_comment(self):
        if randrange(0, 10) > 5:
            return POST_SAYINGS[randrange(0, len(POST_SAYINGS))]
        return None

    def reblog(self):
        posts = self.get_dashboard()
        r_post = self.get_reblog_post(posts)

        try:
            rid = r_post["id"]
            rkey = r_post["reblog_key"]
            rtitle = r_post["blog"]["title"]
            rurl = r_post["short_url"]
            # reblog, like and follow original poster

            comment = self.generate_comment()
            self.client.reblog(
                blogname=self.blog_name, id=rid, reblog_key=rkey, comment=comment
            )
            self.client.like(id=rid, reblog_key=rkey)
            self.follow(r_post, r_post["blog"]["name"])

            # add in a check to see if following the source
            if "source_title" in r_post:
                source = self.client.blog_info(r_post["source_title"])["blog"]
                self.follow(source, source["name"])

            log_message = "Successfully reblogged {0}'s post, {1}".format(rtitle, rurl)
            self.logger.info(log_message)

        except Exception as ex:
            self.logger.error(sys.exc_info()[0])
            raise

    def execute(self):
        self.reblog()
        self.last_executed = datetime.now()
