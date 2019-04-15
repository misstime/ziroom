import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy.exceptions import CloseSpider

import copy
import json
import time
from urllib.parse import urlparse

from ziroom.items import ZiroomItem


class ZiroomSpider(RedisSpider):

    name = 'ziroom'
    custom_settings = {
        'LOG_LEVEL': 'INFO',
        'COOKIES_ENABLED': False,
        'REDIRECT_ENABLED': False,
        'DNS_TIMEOUT': 5,
        'DOWNLOAD_TIMEOUT': 30,
        'CONCURRENT_REQUESTS': 64,
        'CONCURRENT_REQUESTS_PER_IP': 16,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 400, 408, 478, 510],   # 增加：478 510
        'LOG_FILE': 'your log folder path' \
            + time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()) + '.log',   
            # 日志目录必须已存在
        'ITEM_PIPELINES': {
            'ziroom.pipelines.Price': 200,           # 识别价格
            'ziroom.pipelines.SaveMain': 300,        # 保存主干信息
            'ziroom.pipelines.Keeper': 400,          # 管家信息
            'ziroom.pipelines.PaymentAir': 500,      # 支付详情 && 空气质量 && 视频地址
            'ziroom.pipelines.Allocation': 600,      # 房屋配置信息
        }
    }

    def parse(self, response):
        ''''起始页'''
        url_parsed = urlparse(response.url)
        urls_sel = response.xpath('//dl[@class="clearfix zIndex6"]//\
            div[@class="con"]/span[@class="tag"][position()>1]/a/@href').extract()
        if not urls_sel:
            self.log_200_abnormal(response, close=True)
            return
        for url in urls_sel:
            yield scrapy.Request(url_parsed.scheme + ':' + url, callback=self.parse_list)

    def parse_list(self, response):
        '''列表页
        例：http://sh.ziroom.com/z/nl/z3-d310104-b611900103.html
        '''
        self.logger.info(f"crawled 列表页：{response.url}")
        # 价格信息
        # 在列表页而非详情页匹配价格信息，尽量减少请求价格图片时的 request 数量
        price_png_url = response.xpath('//script[contains(text(), \
            "offset_unit")]').re_first(r'image":"//(.+)",')
        price_positions_str = response.xpath('//script[contains(text(), \
            "offset_unit")]').re_first(r'"offset":\[(.+)\]\};')
        if price_png_url and price_positions_str:
            price_png_url = urlparse(response.url).scheme + '://' + price_png_url
            price_positions = list(map(
                lambda x: list(map(int, x.split(','))), 
                price_positions_str.strip('[').strip(']').split('],[')
            ))
        else:
            if response.body.decode().find('我们找不到任何与您的搜索条件匹配的结果') == -1:
                self.log_200_abnormal(
                    response, position='抓取：列表页', 
                    statement='未匹配到价格图片url、价格位置字符串', 
                    close=False
                )
            return

        # 提取部分信息（部分信息只能在列表页提取到）
        sel_info = response.xpath('//ul[@id="houseList"]/li')
        city = response.xpath('//span[@id="curCityName"]/text()').extract_first()
        url_parsed = urlparse(response.url)
        for k, v in enumerate(sel_info):
            item = ZiroomItem()
            item['city'] = city
            item['price'] = {
                'num': None,
                'payment': v.xpath('div[@class="priceDetail"]/p[@class="price"]\
                    /span[@class="gray-6"]/text()').re_first(r'\((.+)\)'),
                'path': None,
                'origin_src': price_png_url,
                'position': price_positions[k],
                'referer':copy.copy(response.url)
            }
            item['title_thumb'] = {
                'path': None,
                'referer': copy.copy(response.url),
                'origin_src': urlparse(response.url).scheme + '://' + \
                    v.xpath('div[@class="img pr"]/a/img/@_src').re_first(r'^//(.+)')
            }
            item['room_id'] = int(v.xpath('div[@class="txt"]/h3/a/@href')\
                .re_first(r'/(\d+)\.html'))
            item['product'] = v.xpath('div[@class="txt"]/h3/a/text()')\
                .re_first(r'(\S+) · .+')
            item['room_name'] = v.xpath('div[@class="txt"]/h3/a/text()')\
                .re_first(r'\S+ · (.+)')
            item['room_style'] = v.xpath('div[@class="txt"]/p[@class="room_tags \
                clearfix"]//span[@class="style"]/text()').extract_first()
            item['is_first_rent'] = v.xpath('div[@class="txt"]/h4/span\
                [@class="green"][contains(text(), "首次出租")]/text()').re_first(r'\S+')
            item['is_near_subway'] = v.xpath('div[@class="txt"]/p[@class="room_tags \
                clearfix"]//span[text()="离地铁近"]/text()').extract_first()
            item['is_private_bathroom'] = v.xpath('div[@class="txt"]/\
                p[@class="room_tags clearfix"]//span[text()="独卫"]/text()').extract_first()
            item['is_private_balcony'] = v.xpath('div[@class="txt"]/\
                p[@class="room_tags clearfix"]//span[text()="独立阳台"]/text()').extract_first()
            item['heating'] = v.xpath('div[@class="txt"]/p[@class=\
                "room_tags clearfix"]//span[text()="集体供暖" \
                or text()="独立供暖" or text()="中央空调"]/text()').extract_first()
            url = v.xpath('div[@class="txt"]/h3/a/@href').re_first(r'//(.+html)')
            yield scrapy.Request(
                url_parsed.scheme + '://' + url, 
                meta={'item': item}, 
                callback=self.parse_detail
            )

        # 每一页：page > 1
        if response.url.find('?p=') < 0:
            total_page = response.xpath('//div[@id="page"]/span[contains(text(), \
                "共")]/text()').re_first(r'共(\d+)页')
            if total_page:
                for v in range(2, int(total_page) + 1):
                    # 为每个请求伪造更合理的 referer，而非都以本次请求地址为 referer
                    url = response.url + '?p=' + str(v)
                    if v == 2:
                        referer = copy.copy(response.url)
                    else:
                        referer = copy.copy(response.url) + '?p=' + str(v-1)
                    yield scrapy.Request(
                        url, 
                        meta={'referer': referer}, 
                        callback=self.parse_list
                    )

    def parse_detail(self, response):
        '''详情页
        例（详情）：http://www.ziroom.com/z/vr/61230316.html
        例（支付详情 && 空气质量）：http://sh.ziroom.com/detail/info?id=61720868&house_id=60273906
        例（管家）：http://sh.ziroom.com/detail/steward?resblock_id=5011102207629&room_id=
            61720868&house_id=60273906&ly_name=&ly_phone=
        例（房屋配置）：http://sh.ziroom.com/detail/config?house_id=60273906&id=61720868
        '''
        self.logger.info(f"crawled 详情页：{response.url}")
        url_parsed = urlparse(response.url)

        # 检测是否正常页面
        room_id = response.xpath('//input[@id="room_id"]/@value').extract_first()
        house_id = response.xpath('//input[@id="house_id"]/@value').extract_first()
        resblock_id = response.xpath('//input[@id="resblock_id"]/@value').extract_first()
        if not(room_id and house_id and resblock_id):
            self.log_200_abnormal(
                response, 
                position='抓取：详情页', 
                statement=f"room_id:{room_id} - house_id:{house_id} - resblock_id:{resblock_id}", 
                close=False
            )
            return

        # 主信息
        item = copy.deepcopy(response.meta['item'])
        item['room_link'] = copy.copy(response.url)
        item['district'] = response.xpath('//span[@class="ellipsis"]/text()')\
            .re(r'\[?(\S+)\s+(\S+)\]?')
        item['house_id'] = int(house_id)
        item['room_sn'] = response.xpath('//h3[@class="fb"]/text()').re_first(r'\S+')
        item['room_introduce'] = response.xpath('//p/strong[text()="房源介绍："]\
            /parent::node()/text()').extract_first()
        item['community'] = response.xpath('//div[@class="node_infor area"]/\
            a[last()]/text()').re_first('(.+)租房信息')
        detail_room = response.xpath('//ul[@class="detail_room"]')
        item['subway'] = detail_room.xpath('li[contains(text(), "交通：")]/span/text() | \
            li[contains(text(), "交通：")]/span/span/p/text()').re(r'距[\s\S+]+米')
        item['rent_type'] = detail_room.xpath('//span[@class="icons"]/text()').extract_first()
        item['area'] = detail_room.xpath('li[contains(text(), "面积：")]/text()')\
            .re_first(r'面积：\s*(\S+)\s+')
        item['floor'] = detail_room.xpath('li[contains(text(), "楼层：")]/text()')\
            .re(r'楼层：\s*(\d+)/(\d+)层')
        item['towards'] = detail_room.xpath('li[contains(text(), "朝向：")]/text()')\
            .re_first(r'朝向：\s*(\S+)\s*')
        item['house_type'] = detail_room.xpath('li[contains(text(), "户型：")]/text()')\
            .re(r'户型：\s*(\d+)室(?:(\d+)厅)?')
        item['rent_status'] = response.xpath('//a[@id="zreserve"]/text()').extract_first()
        img_sel =  response.xpath('//div[@id="lofslidecontent45"]//\
            ul[@class="lof-main-wapper"]/li/a/img')
        if img_sel:
            item['photos'] = []
            for img in img_sel:
                tmp_src = img.xpath('@src').extract_first()
                if tmp_src.find('http:') == -1:
                    tmp_src = url_parsed.scheme + '://' + tmp_src.strip('//').strip('/')
                img_info = {
                    'path': None,
                    'thumb_path': None,
                    'title': img.xpath('@title').extract_first(),
                    'origin_src': tmp_src.replace('v180x135', 'v800x600'),
                }
                item['photos'].append(img_info)
        item['map_position'] = response.xpath('//input[@id="mapsearchText"]/\
            @data-lng | //input[@id="mapsearchText"]/@data-lat').extract()
        roommates_sel = response.xpath('//div[@class="greatRoommate"]/ul/li/div')
        if roommates_sel:
            item['roommates'] = []
            for mate_sel in roommates_sel:
                mate = {}
                mate['gender'] = mate_sel.xpath('parent::node()/@class').re_first(r'\S+')
                mate['room'] = mate_sel.xpath('div[@class="user_top clearfix"]/\
                    p/text()').extract_first()
                mate['status'] = mate_sel.xpath('div[@class="user_top clearfix"]/\
                    span[@class="tags"]/text()').extract_first()
                mate['sign'] = mate_sel.xpath('div[@class="user_center"]/p[1]/\
                    text()').extract_first()
                mate['jobs'] = mate_sel.xpath('div[@class="user_center"]/p[2]/\
                    span[1]/text()').extract_first()
                mate['check_in_time'] = mate_sel.xpath('div[@class="user_bottom"]/\
                    p/text()').re_first(r'\S+')
                item['roommates'].append(mate)
        yield item

        # 继续抓取管家、房间配置、支付详情、空气
        http_prfix = url_parsed.scheme + '://' + url_parsed.netloc
        keeper_url = http_prfix + f"/detail/steward?resblock_id={resblock_id}"\
            f"&room_id={room_id}&house_id={house_id}&ly_name=&ly_phone="
        payment_and_air_url = http_prfix + f"/detail/info?id={room_id}&house_id={house_id}"
        allocation_url = http_prfix + f"/detail/config?house_id={house_id}&id={room_id}"
        yield scrapy.Request(
            keeper_url, 
            meta={'referer': copy.copy(response.url), 'room_id':int(room_id)}, 
            callback=self.parse_keeper
        )
        yield scrapy.Request(
            payment_and_air_url, 
            meta={'referer': copy.copy(response.url), 'room_id':int(room_id)}, 
            callback=self.parse_payment_air
        )
        yield scrapy.Request(
            allocation_url, 
            meta={'referer': copy.copy(response.url), 'room_id':int(room_id)}, 
            callback=self.parse_allocation
        )

    def parse_keeper(self, response):
        '''管家信息'''
        self.logger.info(f"crawled 管家信息：{response.url}")
        try:
            body = response.body.decode()
            body_dict = json.loads(body)
            if body_dict['code'] == 200 and body_dict['message'] == 'success':
                data = body_dict['data']
                item = ZiroomItem()
                item['room_id'] = copy.copy(response.meta['room_id'])
                item['keeper'] = {
                    'keeper_id': int(data['keeperId']),
                    'keeper_name': data['keeperName'],
                    'keeper_phone': data['keeperPhone'],
                    'keeper_header': {
                        'path': None,
                        'origin_src': data['headCorn'],
                        'referer': copy.copy(response.meta['referer']),
                    },
                }
                yield item
            else:
                raise UserWarning(f"管家信息： body_dict['code'] != 200")
        except Exception as e:
            self.log_200_abnormal(response, position='抓取：管家信息', statement=e, close=False)

    def parse_payment_air(self, response):
        '''付款详细信息 && 空气质量'''
        self.logger.info(f"crawled 付款+空气：{response.url}")
        try:
            body = response.body.decode()
            body_dict = json.loads(body)
            if body_dict['code'] == 200 and body_dict['message'] == 'success':
                data = body_dict['data']
                item = ZiroomItem()
                item['room_id'] = copy.copy(response.meta['room_id'])
                if 'payment' in data and len(data['payment']):
                    url_parsed = urlparse(response.url)
                    item['payment'] = {
                        'png': {
                            'origin_src': url_parsed.scheme + ':' + data['payment'][0]['rent'][1], 
                            'referer': copy.copy(response.url), 
                            'path': None
                        },
                        'info': []
                    }
                    for x in data['payment']:
                        pay_tmp = {
                            'period': x['period'],
                            'rent': {'price': None, 'position': x['rent'][2]},
                            'deposit': {'price': None, 'position': x['deposit'][2]},
                            'service_charge': {'price': None, 'position': x['service_charge'][2]},
                        }
                        item['payment']['info'].append(pay_tmp)
                else:
                    item['payment'] = None
                if 'air_part' in data and 'air_quality' in data['air_part']:
                    item['air'] = {
                        'result_list': data['air_part']['air_quality'].get('result_list'),
                        'show_info': data['air_part']['air_quality'].get('show_info')
                    }
                else:
                    item['air'] = None
                item['video_src'] = data.get('vr_video', {}).get('video_url')
                yield item
            else:
                raise UserWarning(f"付款详细信息： body_dict['code'] != 200")
        except Exception as e:
            self.log_200_abnormal(response, position='抓取：付款详细信息', statement=e, close=False)

    def parse_allocation(self, response):
        '''房屋配置'''
        self.logger.info(f"crawled 房屋配置：{response.url}")
        try:
            body = response.body.decode()
            body_dict = json.loads(body)
            if body_dict['code'] == 200 and body_dict['message'] == 'success':
                data = body_dict['data']
                item = ZiroomItem()
                item['room_id'] = copy.copy(response.meta['room_id'])
                item['allocation'] = data
                yield item
            else:
                raise UserWarning(f"房屋配置： body_dict['code'] != 200")
        except Exception as e:
            self.log_200_abnormal(response, position='抓取：房屋配置', statement=e, close=False)

    def log_200_abnormal(self, response, *, position='未知', statement='', close=True):
        ''''记录疑似非正常页面：response.status_code==200，但是返回的页面内容貌似不是我们想要的内容'''
        self.logger.critical(f"发现疑似非正常页面")
        self.logger.critical(f"url : {response.url}")
        self.logger.critical(f"position : {position}")
        self.logger.critical(f"statement : {statement}")
        self.logger.critical(f"response.body : {response.body.decode()}")
        if close:
            raise CloseSpider(f"发现疑似非正常页面")
