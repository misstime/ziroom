from scrapy import Item, Field


class ZiroomItem(Item):
    '''自如'''

    room_name = Field()             # 房间名 - '日光清城4居室-南卧'
    room_id = Field()               # 房间 ID - $int
    house_id = Field()              # 房屋 ID - $int
    room_sn = Field()               # 房间 SN - 'BJZRGZ1118275717'
    room_link = Field()             # 房源链接
    product = Field()               # 产品名 - '友家/整租/直租/豪宅/自如寓'
    city = Field()                  # 城市 - '北京/上海/深圳/杭州/南京/成都/武汉/广州/天津/...'
    district = Field()              # 区 - '东城'
    sub_district = Field()          # 街道/片/村镇 - '安定门'
    community = Field()             # 小区/门牌号 - '安外东河沿'
    subway = Field()                # 地铁 - ['距1号线100米', '距2号线200米', ...]
    rent_type = Field()             # 整租vs合租 - '整租/合租'
    room_style = Field()            # 房屋风格 - '整租4.0 优格'
    price = Field()                 # 租金 - {'price':$int, 'origin_src':$url, 'position':[$int, $int, ...], 'path':$path, 'referer':$url}
    area = Field()                  # 房间面积 - $number
    floor = Field()                 # 房屋楼层 - [$int, $int]
    house_type = Field()            # 户型：x室x厅 - [$int, $int]
    towards = Field()               # 朝向 - '南/北/...'
    is_first_rent = Field()         # 是否首次出租 - True/False
    is_private_bathroom = Field()   # 独卫 - True/False
    is_private_balcony = Field()    # 独立阳台 - True/False
    is_near_subway = Field()        # 临近地铁 - True/False
    heating = Field()               # 供暖方式 - '集体供暖/独立供暖/中央空调'
    title_thumb = Field()           # 房间标题缩略图 - {'path':$path, 'referer':$url, 'origin_src':$url}
    photos = Field()                # 房间图片 - [{'path': '$path', 'thumb_path': '$path', 'title': '$title', 'origin_src':$url, 'referer':$url}, ...]
    room_introduce = Field()        # 房间介绍
    map_position = Field()          # 经纬度 - [$number, $number]
    payment = Field()               # 付款方式详情 - {'png':{'origin_src':$url, 'referer':$url, 'path':$path}, 'info':[{'period':$string, \
        # 'rent':{'price':$int, 'position':$list}, 'deposit':{'price':$int, 'position':$list}, 'service_charge':{'price':$int, 'position':$list}}, ...]}
    roommates = Field()             # 室友信息 - [{'gender':xxx, 'room':xxx, 'status':xxx, 'sign':xxx, 'jobs':xxx, 'check_in_time':xxx}, ...]
    keeper = Field()                # 管家信息 - {'keeper_id':$int, 'keeper_name':$string, 'keeper_phone':$sting, 'keeper_header':{'path':$path, 'origin_src':$url, 'referer':$url}}
    air = Field()                   # 空气质量 - {'result_list':$list, 'show_info':$dict}
    allocation = Field()            # 房间配置 - {"bed":1,"desk":1,"chest":1,"calorifier":0,"washing":1,"microwave":1,"wifi":1,"airCondition":1,"lock":1}
    uptime = Field()                # 更新时间（时间戳） - $int
    rent_status = Field()           # 房间出租状态 - 已出租/未出租
    video_src = Field()             # 房间展示视频地址