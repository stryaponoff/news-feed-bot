import time
import calendar
import feedparser
import re
import logging

# Enable logging
logger = logging.getLogger(__name__)


class Post:
    source_name = None
    timestamp = None
    title = None
    summary = None
    full_text = None
    url = None


class Source:
    """ Base class for news sources """
    name = None
    error = None
    source_url = None
    last_updated = None
    posts = []

    def __init__(self, name, last_updated):
        self.name = name
        self.last_updated = last_updated

    def fetch(self, last_updated):
        self.posts = []
        self.last_updated = last_updated


class Rss(Source):
    posts = []

    def __init__(self, name, src_url, last_updated=time.gmtime(0), yandex_format=False):
        super().__init__(name, last_updated)
        self.source_url = src_url
        self.yandex = yandex_format

    def fetch(self, last_updated):
        super().fetch(last_updated)
        rss = feedparser.parse(self.source_url)

        if rss['feed'] == {}:
            self.error = True

        if not self.error:
            for entry in rss['entries']:
                post = Post()
                post.source_name = self.name
                post.title = entry['title']
                post.summary = entry['summary']
                post.url = entry['link']
                post.timestamp = entry['published_parsed']
                if self.yandex:
                    if 'yandex_full-text' in entry:
                        post.full_text = entry['yandex_full-text']
                if self.last_updated < post.timestamp:
                    self.posts.append(post)


class VkBase(Source):
    def __init__(self, app, name, group_alias, last_updated=time.gmtime(0)):
        super().__init__(name, last_updated)
        self._items = []
        self.app = app
        self.alias = group_alias
        self.owner_id = None

        matches = re.search(r'club(\d+)', self.alias)
        if matches:
            self.owner_id = int('-' + matches.group(1))

    def fetch(self, last_updated):
        super().fetch(last_updated)
        self._items = []

        if self.owner_id is None:
            posts = self.app.vk_api.wall.get(domain=self.alias, count=30)
        else:
            posts = self.app.vk_api.wall.get(owner_id=self.owner_id, count=30)
        for item in posts['items']:
            if item['marked_as_ads'] > 0:
                continue
            self._items.append(item)


class Vk(VkBase):
    posts = []

    def __init__(self, app, name, group_alias, last_updated=time.gmtime(0)):
        super().__init__(app, name, group_alias, last_updated)

    def fetch(self, last_updated):
        super().fetch(last_updated)

        for item in self._items:
            post = Post()
            post.source_name = self.name
            post.title = item['text']
            post.url = 'https://vk.com/{}?w=wall{}_{}'.format(self.alias, item['from_id'], item['id'])
            post.timestamp = time.gmtime(item['date'])
            if self.last_updated < post.timestamp:
                self.posts.append(post)


class VkLinks(VkBase):
    posts = []

    def __init__(self, app, name, group_alias, last_updated=time.gmtime(0)):
        super().__init__(app, name, group_alias, last_updated)

    def fetch(self, last_updated):
        super().fetch(last_updated)

        for item in self._items:
            post = Post()
            post.source_name = self.name
            post.title = item['attachments'][0]['link']['title']
            post.url = item['attachments'][0]['link']['url']
            post.timestamp = time.gmtime(item['date'])
            if self.last_updated < post.timestamp:
                self.posts.append(post)


class Om1(Vk):
    regex = re.compile(r'^(?P<title>.*?)$(?:\n)+^(?:(?P<summary>.*?)$(?:\n)+)?^(?P<url>.*?$)', re.MULTILINE)

    def __init__(self, app, name, group_alias, last_updated=time.gmtime(0)):
        super().__init__(app, name, group_alias, last_updated)

    def fetch(self, last_updated):
        super().fetch(last_updated)

        for post in self.posts:
            try:
                matches = re.search(self.regex, post.title).groupdict()
                if matches['title']:
                    post.title = matches['title']
                if matches['summary']:
                    post.summary = matches['summary']
                if matches['url']:
                    post.url = matches['url']
            except AttributeError as e:
                logger.error(str(e) + ' ' + post.title)


class Mk(Vk):
    def __init__(self, app, name, group_alias, last_updated=time.gmtime(0)):
        super().__init__(app, name, group_alias, last_updated)

    def fetch(self, last_updated):
        super().fetch(last_updated)

        for post in self.posts:
            lines = list(filter(lambda x: x != '', post.title.split('\n')))
            post.title = lines[0]
            if lines[1]:
                post.url = lines[1]
            if lines[2]:
                post.summary = lines[2]
