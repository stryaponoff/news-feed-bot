import time
import feedparser


class Post:
    timestamp = None
    title = None
    summary = None
    full_text = None
    url = None


class Source:
    """ Base class for news sources """
    error = None
    source_url = None
    last_updated = None
    posts = []

    def __init__(self, last_updated):
        self.last_updated = last_updated


class Yandex(Source):
    def __init__(self, src_url, last_updated=0):
        super().__init__(last_updated)
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
