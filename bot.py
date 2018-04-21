#!/usr/bin/python3

import calendar
import json
import logging.handlers
import time
import os

import telegram.error
from telegram.ext import Updater, CommandHandler
from telegram.parsemode import ParseMode

import vk_requests

import Source


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
    SLEEP_TIME = None
    PROXY_URL = None
    PROXY_USERNAME = None
    PROXY_PASSWORD = None
    vk_api = None

    def __init__(self, config_path):
        """ Load settings from config file """
        try:
            f_config = open(config_path, 'r')
            config = json.loads(f_config.read())
            self.API_TOKEN = config['token']
            self.VK_TOKEN = config['vk_token']
            self.CHANNEL_NAME = config['channel_name']
            self.SLEEP_TIME = config['fetch_frequency']
            self.PROXY_URL = config['proxy_url']
            self.PROXY_USERNAME = config['proxy_username']
            self.PROXY_PASSWORD = config['proxy_password']
            self.vk_api = vk_requests.create_api(service_token=self.VK_TOKEN, http_params={'timeout': 30})
            f_config.close()
        except json.JSONDecodeError:
            logger.fatal('JSON decode error in config.json')
            exit()
        except AttributeError as e:
            logger.fatal(str(e))
            exit()

    def read_time(self):
        """ Read last updated timestamp from file """
        try:
            f = open(os.path.dirname(__file__) + '/last_updated', 'r')
            the_time = time.gmtime(float(f.read()))
            f.close()
        except Exception:
            return False

        return the_time

    def write_time(self):
        """ Write last updated timestamp to file """
        try:
            the_time = time.gmtime()
            f = open(os.path.dirname(__file__) + '/last_updated', 'w')
            f.write(str(calendar.timegm(the_time)))
            f.close()
        except Exception:
            return False

        return the_time


# Enable logging
LOG_FILENAME = os.path.dirname(__file__) + '/logfile.log'
LOG_SIZE_BYTES = 1E8
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
    app = App(os.path.dirname(__file__) + '/config.json')

    # Create the Updater and pass it your bot's token.
    updater = Updater(app.API_TOKEN, request_kwargs={
        'read_timeout': 60,
        'connect_timeout': 15,
        'proxy_url': app.PROXY_URL,
        'urllib3_proxy_kwargs': {
            'username': app.PROXY_USERNAME,
            'password': app.PROXY_PASSWORD,
        }
    })

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
    last_updated = app.read_time()
    if not last_updated:
        last_updated = app.write_time()

    sources = [
        Source.Rss('Коммерческие вести', 'http://kvnews.ru/structure/rss/ya', last_updated, True),
        Source.Rss('АиФ в Омске', 'http://www.omsk.aif.ru/rss/all.php', last_updated, True),
        Source.Rss('Омск-Информ', 'http://www.omskinform.ru/rss/news.rss', last_updated),
        Source.Rss('ОмскРегион', 'http://omskregion.info/rss.xml', last_updated),
        Source.Rss('Новый Омск', 'https://newsomsk.ru/rss.php', last_updated),
        Source.Rss('СуперОмск', 'http://superomsk.ru/rss.xml', last_updated),
        Source.Rss('Омскпресс', 'http://omskpress.ru/rss.php', last_updated),
        Source.Rss('Город55', 'https://gorod55.ru/rss', last_updated, True),
        Source.Rss('ОмскЗдесь', 'https://omskzdes.ru/rss/', last_updated),
        Source.Rss('НГС.ОМСК', 'http://news.ngs55.ru/rss/', last_updated),
        Source.Rss('БК55', 'http://bk55.ru/news.rss', last_updated),
        Source.Rss('ВОмске', 'http://vomske.ru/rss/', last_updated),
        Source.Mk(app, 'Московский комсомолец', 'club95760059', last_updated),
        Source.VkLinks(app, 'Вечерний Омск', 'club21276594', last_updated),
        Source.Vk(app, 'Реальный Омск', 'real_0msk', last_updated),
        Source.Vk(app, 'Омск Online', 'omsk_online', last_updated),
        Source.Vk(app, 'Типичный Омск', 'omskpub', last_updated),
        Source.Vk(app, 'Омск Live', 'omsk_live', last_updated),
        Source.Vk(app, '12 канал', 'gtrk_omsk', last_updated),
        Source.Om1(app, 'Om1', 'portal_om1', last_updated),
    ]

    try:
        logging.info('Starting bot...')
        while True:
            logger.info('Fetching new posts...')
            for source in sources:
                try:
                    source.fetch(last_updated)
                except KeyError:
                    continue

                # reverse for chronological representation (newest lower)
                post_list = list(reversed(source.posts))
                while post_list:
                    post = post_list.pop(0)
                    queue.append(post)

            if len(queue) > 0:
                logger.info('Sending new posts...')
            # Sending messages from queue
            while queue:
                post = queue.pop(0)
                title = post.title.replace('_', '\\_')
                title = title.replace('*', '\\*')
                message_text = '{}\n\n_Источник:_ «{}»'.format(title, post.source_name)
                if post.url:
                    # escaping underlines for correct representation with Markdown
                    message_text += '\n{}'.format(post.url).replace('_', '\\_')
                try:
                    result = updater.bot.send_message(
                        chat_id=app.CHANNEL_NAME, text=message_text, parse_mode=ParseMode.MARKDOWN)

                    if result['message_id']:
                        logger.info('Message sent, id = ' + str(result['message_id']))
                    else:
                        logger.error('Message sending error. Telegram returned this: ' + result)
                except telegram.error.BadRequest as e:
                    logger.fatal(str(e))

            # Writing new last_updated value to file
            last_updated = app.write_time()

            logger.info('Job finished. Sleeping for {} secs.'.format(app.SLEEP_TIME))
            time.sleep(app.SLEEP_TIME)
    except KeyboardInterrupt:
        logging.info('Stopping bot...')

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    # updater.idle()


if __name__ == '__main__':
    main()
