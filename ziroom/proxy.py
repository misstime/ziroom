'''代理

代理策略
--------------
每个 request 都会在下载时（通过自定义的下载器）添加代理。
发现 403、302 等状态码时，认定为代理失效，重发当前请求。
下载失败时：检测代理，scrapy 自带 retrymiddleware 接手

使用redis统一调度多个spider的api请求：
------------------------------------------
    proxy_api_locked - 是否锁定api请求（'1'：锁定/禁止请求）
    last_request_time - 上次请求api时间
'''

from scrapy_redis import connection

from scrapy.exceptions import IgnoreRequest
from scrapy.utils.project import get_project_settings

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
# request库禁用安全请求警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)      

from fake_useragent import UserAgent
import json
import time
import logging

from ziroom.utils import mysleep

class Proxy(object):

    _REDIS_KEY_LOCKED = 'proxy:proxy_api_locked'    # redis key：代理API是否被锁定
    _REDIS_KEY_TIME = 'proxy:last_request_time'     # redis key：代理API上次请求时间戳

    def __init__(self):
        project_settings = get_project_settings()
        self.server = connection.from_settings(project_settings) # Redis client
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.ua = UserAgent(path=project_settings['FAKE_JSON_PATH'])
        # 获取代理配置/状态值
        self.proxy = {
            'url': None,            # 代理 url
            'valid': None,          # 代理是否有效（None：未检测/未知，True：有效，False：无效）
            'used_proxy_num': 0,    # 已使用 xxx 个代理
            'api_url': project_settings.get('PROXY_API_URL', None),
                                        # 请求该地址，从代理池获取一个代理
            'api_request_interval': 6,  # 两次请求 api 最短时间间隔         
            'recheck_interval': 10,     # 抓取页面失败时：两次检测代理最小时间间隔
            'rechecked': False,         # 抓取页面失败时：是否重新检测过代理
            'last_check_time': 0,       # 上次检测代理时间
        }
        # 检测代理配置
        self.check_settings = {
            'timeout': 5,                       # 超时时间
            'max_elapsed_seconds': 10,          # 最大响应时间（响应时间大于该值，则判定代理失效）
            'url': 'https://www.baidu.com/',    # 用于检测的 url    
            'request_header': dict(project_settings.get('DEFAULT_REQUEST_HEADERS'))
                                                # 请求header
        }

    def get_proxy(self):
        '''获取一个可用代理。
        从redis中检查已保存的代理，失效或不存在则重新获取（获取新代理后会进行可用性检查）。
        '''
        if self.proxy['valid'] == True:
            return self.proxy['url']
        else:
            cnt = 0
            while self.proxy['valid'] != True:
                res_fetch = self._fetch_new_proxy()    # 获取新代理
                if res_fetch == -1:
                    return None
                elif res_fetch == 0:
                    continue
                elif res_fetch == 1:
                    cnt += 1
                    if cnt > 10:
                        self.logger.info(f"更新代理：失败（检测代理时意外死循环）")
                        return None
                    # 检测代理可用性
                    if self.check_proxy():
                        self.logger.warning(f"更新代理：成功 - {self.proxy['url']}")
                        return self.proxy['url']

    def _fetch_new_proxy(self):
        '''获取新代理（讯代理 ：http://www.xdaili.cn/）
        1) 不检测可用性
        2) 获取成功后，自动设置：
            self.proxy['url'] = 新代理
            self.proxy['valid'] = None
        @:return int 1：成功 0：失败（允许继续请求） -1:失败（不再继续请求）
        '''
        rtn = -1
        # 检测 api 请求是否锁定
        proxy_api_locked = self.server.get(self._REDIS_KEY_LOCKED)
        if proxy_api_locked and proxy_api_locked.decode() == '1':
            self.logger.warning(f"proxy api 已锁定，sleep：{self.proxy['api_request_interval']} s")
            time.sleep(self.proxy['api_request_interval'])
            rtn = 0
        else:
            self.server.set(self._REDIS_KEY_LOCKED, 1)
            last_request_time = self.server.get(self._REDIS_KEY_TIME)
            last_request_time = int(last_request_time.decode()) if last_request_time else 0
            interval = int(time.time()) - last_request_time
            if interval < self.proxy['api_request_interval']:
                sleep_seconds = self.proxy['api_request_interval'] - interval
                self.logger.warning(f"请求代理 API 间隔 < "\
                    f"{self.proxy['api_request_interval']} s，sleep：{sleep_seconds} s")
                time.sleep(sleep_seconds)
            # 请求 api
            self.server.set(self._REDIS_KEY_TIME, int(time.time()))
            try:
                res = requests.get(self.proxy['api_url'])
                res_info = json.loads(res.text)
            except Exception as e:
                self.logger.critical(f"获取新代理失败：请求出错。")
                self.logger.critical(e)
                rtn = 0
            else:
                self.logger.debug(res_info)
                if res.status_code == 200 and res_info['ERRORCODE'] == '0':
                    proxy = ''.join(['http://', res_info['RESULT'][0]['ip'], \
                        ':', res_info['RESULT'][0]['port']])
                    self.proxy['valid'] = None
                    self.proxy['url'] = proxy
                    self.proxy['used_proxy_num'] += 1
                    self.proxy['rechecked'] = False
                    self.proxy['last_check_time'] = 0
                    self.logger.warning(f"获取新代理成功")
                    self.logger.warning(f"proxy: {self.proxy['url']}" \
                        f" used_proxy_num: {self.proxy['used_proxy_num']}")
                    rtn = 1
                elif res.status_code == 200 and res_info['ERRORCODE'] == '10001':
                    self.logger.warning(f"获取新代理失败：系统繁忙。")
                    rtn = 0
                else:
                    self.logger.critical(f"获取新代理失败：其他原因。")
                    self.logger.critical(res_info)
                    rtn = -1
            finally:
                self.server.set(self._REDIS_KEY_LOCKED, '0')
        return rtn

    def check_proxy(self):
        '''检测代理是否失效，并自动设置代理状态
        @:return bool
        '''
        proxy = self.proxy['url']
        self.check_settings['request_header']['User-Agent'] = self.ua.random
        try:
            self.proxy['last_check_time'] = int(time.time())
            r = requests.get(
                url=self.check_settings['url'],
                headers=self.check_settings['request_header'],
                proxies={
                    "https": proxy.replace('http://', ''), 
                    'http': proxy.replace('http://', '')
                },
                timeout=self.check_settings['timeout'],
                verify=False
            )
        except Exception as e:
            self.proxy['valid'] = False
            self.logger.warning(f"检测代理：失效（请求检测地址异常） - {proxy}")
            self.logger.warning(e)
            return False
        else:
            if r.status_code == 200:
                if r.elapsed.seconds > self.check_settings['max_elapsed_seconds']:
                    self.proxy['valid'] = False
                    self.logger.warning(f"检测代理：失效（超时） - {proxy}")
                    self.logger.warning(f"max_elapsed_seconds："\
                        f"{self.check_settings['max_elapsed_seconds']} " \
                            f"elapsed_seconds: {r.elapsed.seconds}")
                    return False
                else:
                    self.proxy['valid'] = True
                    self.logger.warning(f"检测代理：有效 ok - {proxy} - {r.elapsed.seconds}")
                    return True
            else:
                self.proxy['valid'] = False
                self.logger.warning(f"检测代理：失效（status_code != 200） - "\
                    f"{r.status_code} - {proxy}")
                return False

proxy_ins = Proxy()


class ProxyDM(object):
    '''代理 downloader middleware'''

    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def process_response(self, request, response, spider):
        if response.status != 200:
            self.logger.warning(f"发现 {response.status} 页面")
            self.logger.warning(f"proxy：{request.meta['proxy']}")
            self.logger.warning(f"request.url：{request.url}")
            if response.status in (302, 403):
                self.logger.warning(f"{response.status} 页面认定为现ip已被ban，重发请求")
                if proxy_ins.proxy['url'] == request.meta['proxy']:
                    proxy_ins.proxy['valid'] = False
                new_request = request.copy()
                new_request.dont_filter = True
                return new_request
            elif response.status in (503, 510, 478):
                self.logger.warning(f"response.body：{response.body.decode()}")
                #mysleep(3, interval=10)
                pass
        return response

    def process_exception(self, request, exception, spider):
        if not isinstance(exception, IgnoreRequest):
            # 记录异常
            self.logger.warning(f"---------- download 异常 -----------")
            self.logger.warning(f"type(exception)：{type(exception)}")
            self.logger.warning(f"str(exception)：{str(exception)}")
            self.logger.warning(f"request.url：{request.url}")
            self.logger.warning(f"请求代理：{request.meta['proxy']}")
            self.logger.warning(f"当前代理：{proxy_ins.proxy}")
            # 检测代理
            if proxy_ins.proxy['url'] == request.meta['proxy'] and \
                proxy_ins.proxy['valid'] == True:
                if not proxy_ins.proxy['rechecked']:
                    self.logger.warning(f"下载异常：首次复检代理")
                    proxy_ins.check_proxy()
                    proxy_ins.proxy['rechecked'] = True
                else:
                    if int(time.time()) - proxy_ins.proxy['last_check_time'] > \
                        proxy_ins.proxy['recheck_interval']:
                        self.logger.warning(f"下载异常：再次复检代理")
                        proxy_ins.check_proxy()
                    else:
                        self.logger.warning(f"下载异常：复检代理时间未到")


