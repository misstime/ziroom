import logging
import time
from scrapy import signals
from scrapy.exceptions import NotConfigured
from ziroom.pipelines import mongo
        

class CloseSpiderExtension(object):
    '''关闭spider，防止防止空跑，同时关闭mongo连接池。
    关闭条件：
    1、redis_key为空
    2、空闲时间超过 n 个时间单位
    '''

    def __init__(self, idle_number, crawler):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.crawler = crawler
        self.idle_number = idle_number
        self.idle_list = []
        self.idle_count = 0

    @classmethod
    def from_crawler(cls, crawler):
        # 配置仅仅支持RedisSpider
        if 'redis_key' not in dir(crawler.spidercls):
            raise NotConfigured('Only supports RedisSpider')
        idle_number = crawler.settings.getint('IDLE_NUMBER', 30)
        ext = cls(idle_number, crawler)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(ext.spider_idle, signal=signals.spider_idle)
        return ext

    def spider_closed(self, spider):
        self.logger.warning('txmongo 关闭连接池 !')
        mongo.conn_pool.disconnect()

    def spider_idle(self, spider):
        self.idle_count += 1
        self.idle_list.append(int(time.time()))
        idle_list_len = len(self.idle_list)
       
        # 判断 redis 中是否存在关键key, 如果key 被用完，则key就会不存在
        if idle_list_len > 2 and spider.server.exists(spider.redis_key):
            self.idle_list = [self.idle_list[-1]]
        elif idle_list_len > self.idle_number:
            self.logger.warning(f"空闲已持续{self.idle_number}个时间单位，符合spider关闭条件。")
            self.logger.warning("idle start time: {}, close spider time: {}".format(
                self.idle_list[0], self.idle_list[-1]
            ))
            self.logger.warning("total idle time: {} s".format(
                self.idle_list[-1] - self.idle_list[0]
            ))
            # 执行关闭爬虫操作
            self.crawler.engine.close_spider(spider, '长期空闲')


