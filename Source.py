import time
import calendar
import feedparser
import vk_requests
import re


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


class Rss(Source):
    def __init__(self, name, src_url, last_updated=0, yandex_format=False):
        super().__init__(name, last_updated)
        self.source_url = src_url

        rss = feedparser.parse(src_url)

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
                if yandex_format:
                    post.full_text = entry['yandex_full-text']
                if time.mktime(self.last_updated) < calendar.timegm(post.timestamp):
                    self.posts.append(post)


class Vk(Source):
    def __init__(self, app, name, group_alias, last_updated=0):
        super().__init__(name, last_updated)
        self.app = app
        self.alias = group_alias
        self.posts = []

        api = vk_requests.create_api(service_token=app.VK_TOKEN)

        # TODO : Implement offset parameter
        # https://vk.com/dev/wall.get
        posts = api.wall.get(domain=self.alias, count=5)
        for item in posts['items']:
            post = Post()
            post.source_name = self.name
            post.title = item['text']
            post.url = f'https://vk.com/{group_alias}?w=wall{item["from_id"]}_{item["id"]}'
            post.timestamp = time.localtime(item['date'])
            if time.mktime(self.last_updated) < time.mktime(post.timestamp):
                self.posts.append(post)


class Om1(Vk):
    regex = re.compile(r'^(?P<title>.*?)$(?:\n)+^(?:(?P<summary>.*?)$(?:\n)+)?^(?P<url>.*?$)', re.MULTILINE)

    def __init__(self, app, name, group_alias, last_updated=0):
        super().__init__(app, name, group_alias, last_updated)

        for post in self.posts:
            matches = re.search(self.regex, post.title).groupdict()
            if matches['title']:
                post.title = matches['title']
            if matches['summary']:
                post.summary = matches['summary']
            if matches['url']:
                post.url = matches['url']
