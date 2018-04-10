import time
import feedparser
import vk_requests
import re


class Post:
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


class Yandex(Source):
    def __init__(self, name, src_url, last_updated=0):
        super().__init__(name, last_updated)
        self.source_url = src_url

        rss = feedparser.parse(src_url)

        if rss['feed'] == {}:
            self.error = True

        if not self.error:
            for entry in rss['entries']:
                post = Post()
                post.title = entry['title']
                post.summary = entry['summary']
                post.full_text = entry['yandex_full-text']
                post.url = entry['link']
                post.timestamp = entry['published_parsed']
                # print(time.mktime(self.last_updated), time.mktime(post.timestamp))
                if time.mktime(self.last_updated) < time.mktime(post.timestamp):
                    self.posts.append(post)


class Vk(Source):
    def __init__(self, app, name, group_alias, last_updated=0):
        super().__init__(name, last_updated)
        self.app = app
        self.alias = group_alias

        api = vk_requests.create_api(service_token=app.VK_TOKEN)

        # TODO : Implement offset parameter
        # https://vk.com/dev/wall.get
        posts = api.wall.get(domain=self.alias, count=5)
        for item in posts['items']:
            post = Post()
            post.title = item['text']
            post.timestamp = time.localtime(item['date'])
            if time.mktime(self.last_updated) < time.mktime(post.timestamp):
                self.posts.append(post)


class Bk55(Vk):
    regex = re.compile(r'^(?P<title>.*?)$(?:\n)+^(?P<url>.*?)$', re.MULTILINE)

    def __init__(self, app, name, group_alias, last_updated=0):
        super().__init__(app, name, group_alias, last_updated)

        for post in self.posts:
            matches = re.search(self.regex, post.title).groupdict()
            print(post.title, matches)
            if matches['title']:
                post.title = matches['title']
            if matches['url']:
                post.url = matches['url']
