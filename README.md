简介
---

scrapy-redis 抓取自如租房信息 。

依赖
----

所需软件：

- tesseract-ocr = 3.*   # 不建议4.0版本，有bug。
- mongo
- redis

python 库：

- python > 3.0
- scrapy
- txmongo   # 异步mongo，安装：`pip install txmongo`
- redis
- pytesseract       # 图片识别
- fake_useragent    # 随机UserAgent

参考：

[centos7下安装tesseract-ocr进行验证码识别](https://www.cnblogs.com/arachis/p/OCR.html)

自定义配置
--------

#### 必须自定义的配置：

- FILES_STORE 
- TESSDATA_DIR
- MONGO_URI
- MONGO_DATABASE
- MONGO_COLLECTION
- FAKE_JSON_PATH
- REDIS_URL
- LOG_FILE （定义于 `custom_settings` 中）

#### 可能需要自定义的配置：

如果mongo要求权限验证（不要求则忽略）：

- MONGO_USERNAME
- MONGO_PASSWORD

如果使用代理：

- DOWNLOADER -- 开启代理
- PROXY_API_URL -- 配置代理请求地址
- DOWNLOADER_MIDDLEWARES
    - ziroom.proxy.ProxyDM  --开启代理middleware

使用
----

1、手动添加start_urls至redis：

    sadd ziroom:start_urls http://www.ziroom.com/z/nl/z3.html  # 北京
    sadd ziroom:start_urls http://sh.ziroom.com/z/nl/z3.html   # 上海
    sadd ziroom:start_urls http://sz.ziroom.com/z/nl/z3.html   # 深圳
    sadd ziroom:start_urls http://hz.ziroom.com/z/nl/z3.html   # 杭州
    sadd ziroom:start_urls http://nj.ziroom.com/z/nl/z3.html   # 南京
    sadd ziroom:start_urls http://cd.ziroom.com/z/nl/z3.html   # 成都
    sadd ziroom:start_urls http://wh.ziroom.com/z/nl/z3.html   # 武汉
    sadd ziroom:start_urls http://gz.ziroom.com/z/nl/z3.html   # 广州
    sadd ziroom:start_urls http://tj.ziroom.com/z/nl/z3.html   # 天津

2、执行分布式抓取：

    scrapy crawl ziroom

over, thanks for visiting ! :smile:
