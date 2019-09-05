#!/usr/bin/python3
import logging
from pprint import pprint
from datetime import timedelta
from lib.bots import TumblrBot, TumblrBotConfig
from lib.utilities import handle_error

BUCKET_NAME = "tumblr-bot"
KEY = "config/tumblr_config.json"

# Added so that that the logger works correctly
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(name)s - %(message)s",
    datefmt="%m-%d-%Y %H:%M:%S",
)

logging.getLogger("boto3").setLevel(logging.CRITICAL)
logging.getLogger("botocore").setLevel(logging.CRITICAL)


def func_handler(event, context):
    logger = logging.getLogger("MAIN")
    logger.info("Executing {0}".format(context.function_name))

    try:
        config = TumblrBotConfig(bucket=BUCKET_NAME, key=KEY)
        bot = TumblrBot("TBot1", config)
        bot.authenticate()
        bot.execute()

    except Exception as indent:
        handle_error(indent, logger)

    logger.info("Execution complete")


# To run from the command line
if __name__ == "__main__":
    event = type("", (object,), {"type": "command line"})()
    context = type("", (object,), {"function_name": "CLI"})()
    func_handler(event, context)
