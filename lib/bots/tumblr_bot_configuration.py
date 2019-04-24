import logging
import json
import boto3
import botocore


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
