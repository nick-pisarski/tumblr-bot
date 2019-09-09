import logging
import json
import boto3
import botocore

COMMENT_KEY = "config/comments.json"
S3 = boto3.resource("s3")


class TumblrBotConfig:
    def __init__(
        self, config_filepath=None, comment_filepath=None, bucket=None, key=None
    ):
        self.config_filepath = config_filepath
        self.use_local_config = self.config_filepath is not None
        self.comment_filepath = comment_filepath
        self.use_local_comments = self.comment_filepath is not None
        self.comments = []

        self.bucket = bucket
        self.key = key
        self.loaded = False
        self.logger = logging.getLogger(
            "{}({})".format("Config", self.__class__.__name__)
        )

    def set_values(self, obj):
        self.consumer_key = obj["consumer_key"]
        self.consumer_secret = obj["consumer_secret"]
        self.access_token = obj["access_token"]
        self.access_secret = obj["access_token_secret"]

    def load_comments(self):
        self.logger.info("Loading comments")
        try:
            if self.use_local_comments:
                self.logger.info("Filepath found, loading from file.")
                with open(self.comment_filepath, "rb") as f:
                    self.set_values(json.loads(f.read()))
            else:
                self.logger.info("No filepath found, loading from bucket.")
                content_obj = S3.Object(self.bucket, COMMENT_KEY)
                file_content = content_obj.get()["Body"].read().decode("utf-8")
                self.comments = json.loads(file_content)
                self.logger.info("Successfully loaded comments")

        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                self.logger.error(e)
                raise ("The object does not exist.")
            else:
                self.logger.error(e)
                raise

        except Exception as e:
            self.logger.error(e)
            raise Exception("Could not load comments")

    def load(self):
        self.load_comments()
        self.logger.info("Loading config")
        try:
            if self.use_local_config:
                self.logger.info("Filepath found, loading from file.")
                with open(self.config_filepath, "rb") as f:
                    self.set_values(json.loads(f.read()))
            else:
                self.logger.info("No filepath found, loading from bucket.")
                content_obj = S3.Object(self.bucket, self.key)
                file_content = content_obj.get()["Body"].read().decode("utf-8")
                self.set_values(json.loads(file_content))
                self.loaded = True
                self.logger.info("Successfully loaded config")

        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                self.logger.error(e)
                raise ("The object does not exist.")
            else:
                self.logger.error(e)
                raise

        except Exception as e:
            self.logger.error(e)
            raise Exception("Could not access Tumblr configuration file.")
