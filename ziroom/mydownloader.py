from scrapy.core.downloader import Downloader
from scrapy.exceptions import CloseSpider
from ziroom.proxy import proxy_ins

class MyDownloader(Downloader):
    '''自定义下载器：在下载前添加代理。
    针对代理有时效限制的情况，长效代理请无视。
    '''

    def _download(self, slot, request, spider):
        '''在下载前添加代理'''
        proxy = proxy_ins.get_proxy()  # 获取一个可用代理（非异步）
        if proxy:
            request.meta['proxy'] = proxy
        else:
            raise CloseSpider('代理使用失败，关闭 spider')
        
        return super()._download(slot, request, spider)