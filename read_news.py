""" This script is just for testing """

import time
import Source


def read_time():
    try:
        f = open('last_updated', 'r')
        the_time = time.localtime(float(f.read()))
        f.close()
    except Exception:
        return False

    return the_time


def write_time():
    try:
        the_time = time.localtime()
        f = open('last_updated', 'w')
        f.write(str(time.mktime(the_time)))
        f.close()
    except Exception:
        return False

    return the_time


last_updated = read_time()
if not last_updated:
    last_updated = write_time()

kvnews = Source.Yandex('http://kvnews.ru/structure/rss/ya', last_updated)
for post in kvnews.posts:
    print(post)

write_time()  # write new timestamp after updating posts
