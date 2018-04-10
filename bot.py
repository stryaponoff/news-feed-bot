#!/usr/bin/python3

import logging
import json
import time
import Source
from telegram.ext import Updater, CommandHandler
from telegram.parsemode import ParseMode


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


@singleton
class App:
    """ Singleton implements through-app functionality """
    __instance = None
    API_TOKEN = None
    VK_TOKEN = None
    CHANNEL_NAME = None

    def __init__(self, config_path):
        """ Load settings from config file """
        try:
            f_config = open(config_path, 'r')
            config = json.loads(f_config.read())
            self.API_TOKEN = config['token']
            self.VK_TOKEN = config['vk_token']
            self.CHANNEL_NAME = config['channel_name']
            f_config.close()
        except json.JSONDecodeError:
            logger.fatal('JSON decode error in config.json')
            exit()


def read_time():
    """ Read last updated timestamp from file """
    try:
        f = open('last_updated', 'r')
        the_time = time.localtime(float(f.read()))
        f.close()
    except Exception:
        return False

    return the_time


def write_time():
    """ Write last updated timestamp to file """
    try:
        the_time = time.localtime()
        f = open('last_updated', 'w')
        f.write(str(time.mktime(the_time)))
        f.close()
    except Exception:
        return False

    return the_time


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(bot, update):
    """Send a message when the command /help is issued."""
    logger.info(update)
    update.message.reply_text('Help!')


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    # Create an App instance
    app = App('config.json')

    # Create the Updater and pass it your bot's token.
    updater = Updater(app.API_TOKEN, request_kwargs={'read_timeout': 30, 'connect_timeout': 10})

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # log all errors
    dp.add_error_handler(error)

    # init post queue
    queue = []

    # Start the Bot
    updater.start_polling()

    # Set last updated timestamp from file or from current time
    last_updated = read_time()
    if not last_updated:
        # last_updated = write_time()
        last_updated = time.localtime()

    vktest = Source.Bk55(app, 'БК55', 'bk55ru', last_updated)
    for post in vktest.posts:
        queue.append(post)

    kvnews = Source.Yandex('Коммерческие вести', 'http://kvnews.ru/structure/rss/ya', last_updated)
    for post in kvnews.posts:
        queue.append(post)

    # Sending messages from queue
    while queue:
        post = queue.pop(0)
        result = updater.bot.send_message(chat_id=app.CHANNEL_NAME,
                                          text=f'{post.title}\n\n_Источник:_ «{post.source_name}»\n{post.url}',
                                          parse_mode=ParseMode.MARKDOWN)
        if result['message_id']:
            logger.info(f'Message sent, id = {result["message_id"]}')
        else:
            logger.error(f'Message sending error. Telegram return this: {result}')

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
