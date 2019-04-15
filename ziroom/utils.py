'''一些公共函数/类'''

import re
import time
import logging
from functools import reduce
import pytesseract
from PIL import Image
from scrapy.utils.project import get_project_settings

project_settings = get_project_settings()
logger = logging.getLogger(__name__)
sleep_last_time = 0

# 从数字组合出价格
def combine_price(img_str, position):
    if len(img_str) == 10 and len(position) > 0:
        return int(reduce(lambda x, y: x + img_str[y], position, ''))

# 识别图片中数字
def orc_img(img_path):
    config = f'--tessdata-dir {project_settings["TESSDATA_DIR"]} -psm 8 -c '\
        f'tessedit_char_whitelist=1234567890'
    try:
        orc_str = pytesseract.image_to_string(Image.open(img_path), config=config)
    except Exception as e:
        logger.critical(f"orc image failed: {img_path}")
        logger.critical(e)
        return None
    else:
        return orc_str

def mysleep(seconds=1, *, interval=30):
    '''有时间间隔的sleep -- 已废弃'''
    global sleep_last_time

    # if interval < 30:
    #     logger.warning(f"sleep interval set min: 30 S")
    #     interval = 30
    cha = time.time() - sleep_last_time
    if cha > interval:
        logger.warning(f"sleep {seconds} seconds")
        time.sleep(seconds)
        sleep_last_time = time.time()
    else:
        logger.warning(f"wait sleep: {int(interval - cha)}")

def deep_strip(item):
    '''递归strip'''
    if isinstance(item, dict):
        for k, v in enumerate(item):
            item[v] = deep_strip(item[v])
        return item
    elif isinstance(item, list):
        for k, v in enumerate(item):
            item[k] = deep_strip(v)
        return item
    elif isinstance(item, str):
        return item.strip()
    else:
        return item

def remove_wrap(text):
    '''去除字符串中的换行符'''
    if isinstance(text, str):
        return text.replace('\r', '').replace('\n', '').replace(' ', '')
    else:
        return text

def string2number(obj):
    '''string 转 number（int 或 float）'''
    if isinstance(obj, str):
        if re.match(r'^\d+$', obj):
            return int(obj)
        elif re.match(r'^[\d\.]+$', obj) and len(obj.split('.')) == 2:
            return float(obj)
        else:
            return obj
    elif isinstance(obj, list):
        for k, v in enumerate(obj):
            obj[k] = string2number(v)
        return obj
    elif isinstance(obj, dict):
        for k, v in enumerate(obj):
            obj[v] = string2number(obj[v])
        return obj
    else:
        return obj

