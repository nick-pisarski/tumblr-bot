import os
import sys
import json
import logging
import boto3
import botocore

from urllib.parse import parse_qsl
from random import randrange
from datetime import datetime
from pprint import pprint
from .bot_base import AbstractBotClass

import oauth2
import pytumblr

REQUEST_TOKEN_URL = "http://www.tumblr.com/oauth/request_token"
AUTHORIZATION_URL = "http://www.tumblr.com/oauth/authorize"
ACCESS_TOKEN_URL = "http://www.tumblr.com/oauth/access_token"
MAX_FOLLOW_LIMIT = 1000
REBLOG_CHECK_LIMIT = 100

logging.getLogger("boto3").setLevel(logging.CRITICAL)
logging.getLogger("botocore").setLevel(logging.CRITICAL)


class TumblrBotConfig:
    def __init__(self, filepath=None, bucket=None, key=None):
        self.filepath = filepath
        self.use_file_path = self.filepath is not None
        self.bucket = bucket
        self.key = key
        self.loaded = False
        self.logger = logging.getLogger(
            "{}({})".format("tumbler_config", self.__class__.__name__)
        )

    def set_values(self, obj):
        self.consumer_key = obj["consumer_key"]
        self.consumer_secret = obj["consumer_secret"]
        self.access_token = obj["access_token"]
        self.access_secret = obj["access_token_secret"]

    def load(self):
        try:
            if self.use_file_path:
                self.logger.info("Filepath found, loading from file.")
                with open(self.filepath, "rb") as f:
                    self.set_values(json.loads(f.read()))
            else:
                self.logger.info(
                    "No filepath found, loading from s3 bucket: {}".format(self.bucket)
                )
                s3 = boto3.resource("s3")
                content_obj = s3.Object(self.bucket, self.key)
                file_content = content_obj.get()["Body"].read().decode("utf-8")
                self.set_values(json.loads(file_content))
                self.loaded = True

        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                print(e)
                raise ("The object does not exist.")
            else:
                print(e)
                raise

        except Exception as e:
            print(e)
            raise Exception("Could not access Tumblr configuration file.")


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
        return r_post

    def reblog(self):
        posts = self.get_dashboard()
        r_post = self.get_reblog_post(posts)

        try:
            rid = r_post["id"]
            rkey = r_post["reblog_key"]
            rtitle = r_post["blog"]["title"]
            rurl = r_post["short_url"]
            # reblog, like and follow original poster
            self.client.reblog(blogname=self.blog_name, id=rid, reblog_key=rkey)
            self.client.like(id=rid, reblog_key=rkey)
            self.follow(r_post, r_post["blog"]["name"])

            # add in a check to see if following the source
            if "source_title" in r_post:
                source = self.client.blog_info(r_post["source_title"])["blog"]
                self.follow(source, source["name"])

            # TODO revisit the information that gets logged on a sucess
            log_message = "Successfully reblogged {0}'s post, {1}".format(rtitle, rurl)
            self.logger.info(log_message)

        except Exception as ex:
            self.logger.error(sys.exc_info()[0])
            raise

    def execute(self):
        self.reblog()
        self.last_executed = datetime.now()
