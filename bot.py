#!/usr/bin/python3

import logging
import logging.handlers
import json
import time
import Source
from telegram.ext import Updater, CommandHandler
from telegram.parsemode import ParseMode
import telegram.error


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
        except AttributeError as e:
            logger.fatal(str(e))
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
LOG_FILENAME = 'logfile.log'
LOG_SIZE_BYTES = 1E6
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
log_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=LOG_SIZE_BYTES, backupCount=5)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)


def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Привет!')


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

    sources = [
        Source.Rss('Омск-Информ', 'http://www.omskinform.ru/rss/news.rss', last_updated),
        Source.Rss('Город55', 'https://gorod55.ru/rss', last_updated, True),
        Source.Rss('Коммерческие вести', 'http://kvnews.ru/structure/rss/ya', last_updated, True),
        Source.Rss('БК55', 'http://bk55.ru/news.rss', last_updated),
        Source.Rss('ОмскЗдесь', 'https://omskzdes.ru/rss/', last_updated),
        Source.Rss('НГС.ОМСК', 'http://news.ngs55.ru/rss/', last_updated, True),
        Source.Rss('Новый Омск', 'https://newsomsk.ru/rss.php', last_updated),
        Source.Rss('Омскпресс', 'http://omskpress.ru/rss.php', last_updated),
        Source.Rss('АиФ в Омске', 'http://www.omsk.aif.ru/rss/all.php', last_updated, True),
        Source.Rss('ОмскРегион', 'http://omskregion.info/rss.xml', last_updated),
        Source.Om1(app, 'Om1', 'portal_om1', last_updated),
        Source.Vk(app, '12 канал', 'gtrk_omsk', last_updated),
        Source.Mk(app, 'Московский комсомолец', 'club95760059'),
    ]
    for source in sources:
        # reverse for chronological representation (newest lower)
        for post in reversed(source.posts):
            queue.append(post)

    # Sending messages from queue
    while queue:
        post = queue.pop(0)
        message_text = f'{post.title}\n\n_Источник:_ «{post.source_name}»'
        if post.url:
            # escaping underlines for correct representation with Markdown
            message_text += f'\n{post.url}'.replace('_', '\\_')
        try:
            result = updater.bot.send_message(
                chat_id=app.CHANNEL_NAME, text=message_text, parse_mode=ParseMode.MARKDOWN)

            if result['message_id']:
                logger.info(f'Message sent, id = {result["message_id"]}')
            else:
                logger.error(f'Message sending error. Telegram return this: {result}')
        except telegram.error.BadRequest as e:
            logger.fatal(str(e))

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
