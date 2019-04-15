from scrapy import signals

from fake_useragent import UserAgent


class RandomUserAgentDM(object):
    '''随机UA - downloader middleware'''

    def __init__(self, crawler):
        fake_json_path = crawler.settings['FAKE_JSON_PATH']
        self.ua = UserAgent(path=fake_json_path)

    def process_request(self, request, spider):
        request.headers['User-Agent'] = self.ua.random

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
