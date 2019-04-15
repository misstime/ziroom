BOT_NAME = 'ziroom'

SPIDER_MODULES = ['ziroom.spiders']
NEWSPIDER_MODULE = 'ziroom.spiders'


# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
}

DOWNLOADER_MIDDLEWARES = {
    'ziroom.middlewares.RandomUserAgentDM': 450,
    'ziroom.proxy.ProxyDM': 755,
}

EXTENSIONS = {
    'ziroom.extensions.CloseSpiderExtension': 300,
}
# 超过 xxx 个空闲时间单位时，关闭spider
IDLE_NUMBER = 30    

DOWNLOADER = 'ziroom.mydownloader.MyDownloader'

# 下载文件(FilesPipeline、ImagesPipeline)
FILES_EXPIRES = 1000
FILES_STORE = 'your folder path'


# ------------------------- scrapy 无关 -------------------------

# pytesseract（图片识别库，版本要求：3.0 -- (4.0版本有bug)）配置，亦可配置在系统变量中。
# 配置值为安装 pytesseract 后，tessdata 文件夹的路径
TESSDATA_DIR = 'your folder path'

MONGO_URI = 'your mogno uri'    # 格式：mongodb://localhost:27017
MONGO_POOL_SIZE = 100
MONGO_DATABASE = 'your mongo database'     
MONGO_COLLECTION = 'your mongo collection'
# mongo权限验证（不需要密码登录可留空）： 
MONGO_USERNAME = 'your mongo user'
MONGO_PASSWORD = 'your mongo passwd'

# fake_user_agent 本地数据文件地址
FAKE_JSON_PATH = 'your file path'

# 代理获取地址
PROXY_API_URL = 'your proxy_api_url'


# ------------------------- scrapy-redis -------------------------

# Enables scheduling storing requests queue in redis.
SCHEDULER = "scrapy_redis.scheduler.Scheduler"

# Ensure all spiders share same duplicates filter through redis.
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"

# Default requests serializer is pickle, but it can be changed to any module
# with loads and dumps functions. Note that pickle is not compatible between
# python versions.
# Caveat: In python 3.x, the serializer must return strings keys and support
# bytes as values. Because of this reason the json or msgpack module will not
# work by default. In python 2.x there is no such issue and you can use
# 'json' or 'msgpack' as serializers.
# SCHEDULER_SERIALIZER = "scrapy_redis.picklecompat"

# Don't cleanup redis queues, allows to pause/resume crawls.
SCHEDULER_PERSIST = True

# Schedule requests using a priority queue. (default)
# 优先级队列 - 深度优先
SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.PriorityQueue'
DEPTH_PRIORITY = -1     

# Alternative queues.
# 先进先出队列（广度优先）
#SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.FifoQueue'
# 后进先出队列（深度优先）
#SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.LifoQueue'

# Max idle time to prevent the spider from being closed when distributed crawling.
# This only works if queue class is SpiderQueue or SpiderStack,
# and may also block the same time when your spider start at the first time (because the queue is empty).
# SCHEDULER_IDLE_BEFORE_CLOSE = 10

# Store scraped item in redis for post-processing.
# ITEM_PIPELINES = {
#     'scrapy_redis.pipelines.RedisPipeline': 300
# }

# The item pipeline serializes and stores the items in this redis key.
REDIS_ITEMS_KEY = '%(spider)s:items'

# The items serializer is by default ScrapyJSONEncoder. You can use any
# importable path to a callable object.
#REDIS_ITEMS_SERIALIZER = 'json.dumps'

# Specify the host and port to use when connecting to Redis (optional).
# REDIS_HOST = 'localhost'
# REDIS_PORT = 6379

# Specify the full Redis URL for connecting (optional).
# If set, this takes precedence over the REDIS_HOST and REDIS_PORT settings.
# 格式：'redis://user:passwd@host:port'
# 例子：'redis://:foobar@121.121.121.121:6379   # 用户名可留空
REDIS_URL = 'your redis uri'

# Custom redis client parameters (i.e.: socket timeout, etc.)
#REDIS_PARAMS  = {}
# Use custom redis client class.
#REDIS_PARAMS['redis_cls'] = 'myproject.RedisClient'

# If True, it uses redis' ``SPOP`` operation. You have to use the ``SADD``
# command to add URLs to the redis queue. This could be useful if you
# want to avoid duplicates in your start urls list and the order of
# processing does not matter.
REDIS_START_URLS_AS_SET = True

# Default start urls key for RedisSpider and RedisCrawlSpider.
REDIS_START_URLS_KEY = '%(name)s:start_urls'

# Use other encoding than utf-8 for redis.
#REDIS_ENCODING = 'latin1'



