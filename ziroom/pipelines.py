import os
import re
import copy
import time
import logging
import hashlib

from functools import reduce
import pytesseract
from PIL import Image

from twisted.internet.defer import inlineCallbacks, returnValue, Deferred
from twisted.internet.threads import deferToThread
from twisted.python.failure import Failure

from txmongo.connection import ConnectionPool

import scrapy
from scrapy.exceptions import DropItem
from scrapy.utils.python import to_bytes
from scrapy.utils.project import get_project_settings
from scrapy.pipelines.images import FilesPipeline

from ziroom.utils import deep_strip, remove_wrap, string2number, orc_img, combine_price

project_settings = get_project_settings()


class MongoClient(object):
    
    def __init__(self):
        self.closed = False
        self.conn_pool = ConnectionPool(
            project_settings['MONGO_URI'], 
            pool_size=project_settings.get('MONGO_POOL_SIZE', 1)
        )
        self.db = self.conn_pool[project_settings['MONGO_DATABASE']]
        self.db.authenticate(
            project_settings['MONGO_USERNAME'], 
            project_settings['MONGO_PASSWORD'], 
        )
        self.col = self.db[project_settings['MONGO_COLLECTION']]

mongo = MongoClient()


class Price(FilesPipeline):
    '''下载价格图片，识别数值
    使用 FilesPipeline 而非 ImagesPipeline，便于图片识别。
    '''

    logger = logging.getLogger(__name__ + '.' + 'Price')
    img_cache = {}

    def get_media_requests(self, item, info):
        if 'price' in item and item['price']:
            yield scrapy.Request(
                copy.copy(item['price']['origin_src']),
                headers={'referer': copy.copy(item['price']['referer'])},
            )

    def item_completed(self, results, item, info):
        if item.get('price'):
            is_success, file_info = results[0]
            if is_success:
                img_path = project_settings['FILES_STORE'].rstrip('/')\
                    .rstrip('\\') + '/' + file_info['path']
                img_str = self.img_cache.get(file_info['path'])
                price_num = None
                if img_str:
                    self.logger.info("图片已识别：{} - {} {}".format(
                        img_str,
                        item['room_id'],
                        img_path,
                    ))
                    price_num = combine_price(img_str, item['price']['position'])
                else:
                    img_str = orc_img(img_path)
                    if img_str:
                        self.logger.info("识别图片：{} - {} {}".format(
                            img_str,
                            item['room_id'],
                            img_path,
                        ))
                        if len(self.img_cache) > 100:
                            self.img_cache.clear()
                        self.img_cache[file_info['path']] = img_str
                        price_num = combine_price(img_str, item['price']['position'])
                    else:
                        self.logger.critical(f"识别图片失败：{img_path}")
                item['price']['path'] = img_path
                item['price']['num'] = price_num
                if price_num:
                    self.logger.info(f"价格 {item['room_id']}: {price_num}")
                else:
                    self.logger.info(f"价格识别失败: {item['room_id']}")
            else:
                self.logger.warning(f"下载 价格图片 {item['room_id']}：failed -- "\
                    f"{item['price']['origin_src']}")
                self.logger.warning(file_info)
        return item

    def file_path(self, request, response=None, info=None):
        media_guid = hashlib.sha1(to_bytes(request.url)).hexdigest()
        media_ext = os.path.splitext(request.url)[1]
        tail_dir_name = media_guid[0:2]
        return '{}/{}{}'.format(
            tail_dir_name, 
            media_guid, 
            media_ext
        )


class SaveMain(object):
    '''保存主干信息，部分信息由其他管道保存'''

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    @inlineCallbacks
    def process_item(self, item, spider):
        if item.get('room_name'):
            self.format_item(item)
            try:
                item['uptime'] = int(time.time())
                res = yield mongo.col.update(
                    {'room_id': item['room_id']}, 
                    {'$set': dict(item)}, 
                    upsert=True
                )
                self.logger.warning(f"保存主干信息 {item['room_id']}")
                self.logger.debug(res)
            except Exception as e:
                self.logger.critical(f"保存主干信息 Exception: ")
                self.logger.critical(e)
        returnValue(item)

    def format_item(self, item):
        item = deep_strip(item)
        # 地铁信息
        if item['subway']:
            for k, v in enumerate(item['subway']):
                item['subway'][k] = remove_wrap(v)
        # area、floor、house_type、map_position
        item['area'] = string2number(item['area'])
        item['floor'] = string2number(item['floor'])
        item['house_type'] = string2number(item['house_type'])
        item['map_position'] = string2number(item['map_position'])
        # 房间介绍
        item['room_introduce'] = remove_wrap(item['room_introduce'])
        # 区、街道
        if len(item['district']) == 2:
            item['district'], item['sub_district'] = tuple(item['district'])
        # 是否临近地铁、独卫、独立阳台、首次出租
        item['is_near_subway'] = (True if item['is_near_subway'] == '离地铁近' else False)
        item['is_private_bathroom'] = (True if item['is_private_bathroom'] == '独卫' else False)
        item['is_private_balcony'] = (True if item['is_private_balcony'] == '独立阳台' else False)
        item['is_first_rent'] = (True if item['is_first_rent'] == '首次出租' else False)
        # 整租 & 合租
        if item['rent_type'] in ['整', '合']:
            item['rent_type'] = ''.join((item['rent_type'], '租'))
        else:
            item['rent_type'] = None
        # 出租状态
        item['rent_status'] = '未出租' if item['rent_status'] == '我要看房' else item['rent_status']
        # 室友信息
        none_tuple = ('…', '...', '未知')
        if 'roommates' in item and len(item['roommates']) > 0:
            for ke, va in enumerate(item['roommates']):
                for k, v in va.items():
                    if v in none_tuple:
                        item['roommates'][ke][k] = None
                        continue
                    elif k == 'gender':
                        if v == 'man':
                            item['roommates'][ke][k] = '男'
                        elif v == 'woman':
                            item['roommates'][ke][k] = '女'
                        else:
                            item['roommates'][ke][k] = None


class Keeper(object):
    '''管家信息'''

    logger = logging.getLogger(__name__ + '.' + 'Keeper')

    @inlineCallbacks
    def process_item(self, item, spider):
        if item.get('keeper'):
            # 保存数据
            try:
                res = yield mongo.col.update(
                    {'room_id': item['room_id']},
                    {'$set': {'keeper': dict(item['keeper']), 'uptime': int(time.time())}},
                    upsert=True
                )
                self.logger.warning(f"保存 管家信息 {item['room_id']}")
                self.logger.debug(res)
            except Exception as e:
                self.logger.critical(f"保存管家信息 Exception: ")
                self.logger.critical(e)
        returnValue(item)


class PaymentAir(FilesPipeline):
    '''支付详情 && 空气质量'''

    logger = logging.getLogger(__name__ + '.' + 'PaymentAir')

    def get_media_requests(self, item, info):
        if item.get('payment'):
            yield scrapy.Request(
                copy.copy(item['payment']['png']['origin_src']),
                headers={
                    'referer': copy.copy(item['payment']['png']['referer'])
                },
            )

    @inlineCallbacks
    def item_completed(self, results, item, info):
        if item.get('payment'):
            is_success, file_info = results[0]
            if is_success:
                self.logger.info(
                    '下载 支付详情价格图片 {}：ok -- {}'.format(
                        item['room_id'], 
                        item['payment']['png']['origin_src']
                    )
                )
                img_path = project_settings['FILES_STORE'].rstrip('/').rstrip('\\') \
                    + '/' + file_info['path']
                item['payment']['png']['path'] = img_path
                img_str = yield orc_img(img_path)
                if img_str:
                    self.logger.info("识别图片：{} - {} {}".format(
                        img_str,
                        item['room_id'],
                        img_path,
                    ))
                    for x in item['payment']['info']:
                        x['rent']['price'] = combine_price(
                            img_str, 
                            x['rent']['position']
                        )
                        x['deposit']['price'] = combine_price(
                            img_str, 
                            x['deposit']['position']
                            )
                        x['service_charge']['price'] = combine_price(
                            img_str, 
                            x['service_charge']['position']
                        )
                        self.logger.debug(
                            "支付详情 {} - {} ORC：deposit-{} rent-{} service_charge-{}".format(
                                item['room_id'],
                                x['period'],
                                x['deposit']['price'],
                                x['rent']['price'],
                                x['service_charge']['price'],
                            )
                        )
                else:
                    self.logger.critical(f"识别图片失败：{img_path}")
            else:
                self.logger.warning(
                    "下载 支付详情价格图片 {}：failed -- {}".format(
                        item['room_id'],
                        item['payment']['png']['origin_src']
                    )
                )
                self.logger.warning(file_info)
            # 保存数据
            try:
                item['uptime'] = int(time.time())
                res = yield mongo.col.update(
                    {'room_id': item['room_id']},
                    {'$set': dict(item)},
                    upsert=True
                )
                self.logger.warning(f"保存 支付详情&&空气质量信息 {item['room_id']}")
                self.logger.debug(res)
            except Exception as e:
                self.logger.critical(f"保存支付详情 Exception: ")
                self.logger.critical(e)
        returnValue(item)

    def file_path(self, request, response=None, info=None):
        media_guid = hashlib.sha1(to_bytes(request.url)).hexdigest()
        media_ext = os.path.splitext(request.url)[1]
        tail_dir_name = media_guid[0:2]
        settings = get_project_settings()
        return '{}/{}{}'.format(
            tail_dir_name, 
            media_guid, 
            media_ext
        )


class Allocation(object):
    '''房间配置'''

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    @inlineCallbacks
    def process_item(self, item, spider):
        if item.get('allocation'):
            try:
                item['uptime'] = int(time.time())
                res = yield mongo.col.update(
                    {'room_id': item['room_id']},
                    {'$set': dict(item)},
                    upsert=True
                )
                self.logger.warning(f"保存 房屋配置信息 {item['room_id']}")
                self.logger.debug(res)
            except Exception as e:
                self.logger.critical(f"保存房屋配置 Exception: ")
                self.logger.critical(e)
        returnValue(item)











