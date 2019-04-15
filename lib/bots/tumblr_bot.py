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

REQUEST_TOKEN_URL = 'http://www.tumblr.com/oauth/request_token'
AUTHORIZATION_URL = 'http://www.tumblr.com/oauth/authorize'
ACCESS_TOKEN_URL = 'http://www.tumblr.com/oauth/access_token'
REBLOGGED_KEYS_LENGTH = 100
MAX_FOLLOW_LIMIT = 1000
REBLOG_CHECK_LIMIT = 50


class TumblrBotConfig:
    def __init__(self, filepath=None, bucket=None, key=None):
        self.filepath = filepath
        self.use_file_path = self.filepath is not None
        self.bucket = bucket
        self.key = key
        self.loaded = False
        self.logger = logging.getLogger(
            '{}({})'.format("tumbler_config", self.__class__.__name__))

    def set_values(self, obj):
        self.consumer_key = obj['consumer_key']
        self.consumer_secret = obj['consumer_secret']
        self.access_token = obj['access_token']
        self.access_secret = obj['access_token_secret']

    def load(self):
        try:
            if self.use_file_path:
                self.logger.info('Filepath found, loading from file.')
                with open(self.filepath, 'rb') as f:
                    self.set_values(json.loads(f.read()))
            else:
                self.logger.info(
                    'No filepath found, loading from s3 bucket: {}'.format(self.bucket))
                s3 = boto3.resource('s3')
                content_obj = s3.Object(self.bucket, self.key)
                file_content = content_obj.get()['Body'].read().decode('utf-8')
                self.set_values(json.loads(file_content))
                self.loaded = True

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
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
        self.reblogged_keys = []

        if config is None:
            raise Exception("Configuration not given")

        self.config = config
        self.config.load()

    def get_access(self):
        # WIP for some reason the token and secret that comes back are not authorized
        consumer = oauth2.Consumer(
            self.config.consumer_key, self.config.consumer_secret)
        oclient = oauth2.Client(consumer)

        resp, content = oclient.request(REQUEST_TOKEN_URL, "GET")
        request_token = dict(parse_qsl(content.decode("utf-8")))
        self.access_token = request_token['oauth_token']
        self.access_secret = request_token['oauth_token_secret']
        self.has_access = True

    def authenticate(self):

        self.client = pytumblr.TumblrRestClient(
            self.config.consumer_key, self.config.consumer_secret, self.config.access_token, self.config.access_secret)

        info = self.client.info()
        if info['user']:
            self.user = info['user']

        try:
            if 'meta' in info:
                if info['meta']['status'] == 401:
                    self.authenticated = False
                    self.logger.error('Authenication failed: {0}, {1}'.format(info['meta']['status'],
                                                                              info['meta']['msg']))
            else:
                self.authenticated = True
                self.logger.info('Successfully authenticated.')

        except Exception as ex:
            self.authenticated = False
            self.logger.error(sys.exc_info()[0])
            raise

    def get_dashboard(self, limit=REBLOG_CHECK_LIMIT):
        return self.client.dashboard(limit=limit)['posts']

    def follow(self, post, name):
        # check if client account is following the blogger and follow if the number be followed
        # less than the limit defined
        if not post['followed'] and self.user['following'] < MAX_FOLLOW_LIMIT:
            self.client.follow('{}.tumblr.com'.format(name))
            self.logger.info('Followed {0}'.format(name))

    def reblog(self):
        blog_name = self.user['blogs'][0]['name']
        posts = self.get_dashboard()

        # only get posts that can reblogged
        # TODO move move post selection to its own function and add in
        # the ability to NOT select a post that has already been posted
        filtered_posts = [p for p in posts if(
            p['can_reblog'] and (p['blog_name'] != blog_name))]

        # grab a random post from the filtered posts to reblog
        # and keep trying until one is found that hasnt been blogged
        r_post = filtered_posts[randrange(0, len(filtered_posts))]
        while r_post['reblog_key'] in self.reblogged_keys:
            r_post = filtered_posts[randrange(0, len(filtered_posts))]

        try:
            # reblog, like and follow original poster
            self.client.reblog(
                blogname=blog_name, id=r_post['id'], reblog_key=r_post['reblog_key'])
            self.client.like(id=r_post['id'], reblog_key=r_post['reblog_key'])

            # add in check to make sure blog doesnt follow itself
            self.follow(r_post, r_post['blog_name'])

            # keep track of the last few calls
            # NOTE: since this only gets runned once a running list of reblogged keys cannot
            # be kept in memory, should update this to compare to the last 50 post from this
            # account
            self.reblogged_keys.append(r_post['reblog_key'])
            if(len(self.reblogged_keys) > REBLOGGED_KEYS_LENGTH):
                self.reblogged_keys.pop(0)

            # add in a check to see if following the source
            if 'source_title' in r_post:
                source = self.client.blog_info(r_post['source_title'])['blog']
                if source['name'] is not blog_name:
                    self.follow(source, source['name'])

            # TODO revisit the information that gets logged on a sucess
            self.logger.info('Successfully reblogged {0}, {1}'.format(
                r_post['reblog_key'], r_post['blog_name']))

        except Exception as ex:
            self.logger.error(sys.exc_info()[0])
            raise

    def execute(self):
        self.reblog()
        self.last_executed = datetime.now()
