#!/usr/bin/python3
import logging
from pprint import pprint
from datetime import timedelta
from lib.bots import TumblrBot

# Added so that that the logger works correctly
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(name)s - %(message)s',
    datefmt='%m-%d-%Y %H:%M:%S'
)


def func_handler(event, context):
    logger = logging.getLogger('MAIN')
    logger.info('Executing {0}'.format(context.function_name))

    try:
        bot = TumblrBot('TBot1', 'config/tumblr_config.json')
        bot.authenticate()
        bot.execute()
    except Exception as indent:
        logger.error("Error: {0}".format(indent))

    logger.info('Execution complete')
