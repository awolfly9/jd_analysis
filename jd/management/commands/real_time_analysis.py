#-*- coding: utf-8 -*-

import logging
import sys
import matplotlib
import time

matplotlib.use('Agg')

import os
import config
import utils
import redis
import markdown2

from scrapy.utils.log import configure_logging
from django.core.management.base import BaseCommand
from wordcloud import WordCloud
from sqlhelper import SqlHelper
from django.conf import settings
from pandas import Series, DataFrame
from cus_exception import CusException
from jd.analysis_jd_item import Analysis
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


# python manage.py
class Command(BaseCommand):
    help = 'analysis jd comment data'

    def add_arguments(self, parser):
        parser.add_argument('-a', action = 'append', dest = 'spargs', default = [],
                            help = 'set spider argument (may be repeated)')

    #必须实现的方法
    def handle(self, *args, **options):
        reload(sys)
        sys.setdefaultencoding('utf-8')
        os.chdir(sys.path[0])

        spargs = utils.arglist_to_dict(options['spargs'])

        if not os.path.exists('log'):
            os.makedirs('log')

        configure_logging(install_root_handler = False)
        logging.basicConfig(
                filename = 'log/%s.log' % spargs.get('product_id'),
                format = '%(levelname)s %(asctime)s: %(message)s',
                level = logging.ERROR
        )

        guid = spargs.get('guid', '0')
        product_id = spargs.get('product_id', '0')

        if guid == '0' or product_id == '0':
            utils.log('分析数据传入参数不对，接收到的参数为： spargs:%s' % spargs)
            utils.push_redis(guid = guid, product_id = product_id, info = '分析数据传入参数不对，接收到的参数为:%s' % spargs)
            utils.push_redis(guid = guid, product_id = product_id, info = 'finish')
            return

        utils.log('开始分析：%s' % spargs)
        sql = SqlHelper()
        red = redis.StrictRedis(host = config.redis_host, port = config.redis_part, db = config.redis_db,
                                password = config.redis_pass)
        spargs['sql'] = sql
        spargs['red'] = red

        # 运行爬虫
        runspider(spargs)

        # 开启分析
        analysis = RealTimeAnalysis(**spargs)
        analysis.run()


def runspider(spargs):
    url = spargs.get('url')
    name = spargs.get('name', 'jd')

    if not os.path.exists('log'):
        os.makedirs('log')

    configure_logging(install_root_handler = False)
    logging.basicConfig(
            filename = 'log/%s.log' % name,
            format = '%(levelname)s %(asctime)s: %(message)s',
            level = logging.ERROR
    )
    print "get_project_settings().attributes:", get_project_settings().attributes['SPIDER_MODULES']
    process = CrawlerProcess(get_project_settings())
    start_time = time.time()
    try:
        logging.info('进入爬虫')
        process.crawl(name, **spargs)
        process.start()
    except Exception, e:
        process.stop()
        logging.error("url:%s, errorMsg:%s" % (url, e.message))
    finally:
        logging.error("url:%s, errorMsg:%s" % (url, "爬虫终止"))

    utils.log('spider crawl time:%s' % str(time.time() - start_time))


# 注意考虑到多个商品对比的情况
class RealTimeAnalysis(Analysis):
    def __init__(self, **kwargs):
        super(RealTimeAnalysis, self).__init__(**kwargs)

    def record_result(self, result, color = 'default', font_size = 16, strong = False, type = 'word',
                      br = True, default = False, new_line = False):
        self.full_result = ''
        if type == 'word' and default == False:
            if strong:
                result = '<strong style="color: %s; font-size: %spx;">%s</strong>' % (color, font_size, result)
            else:
                result = '<span style="color: %s; font-size: %spx;">%s</span>' % (color, font_size, result)
        elif type == 'image':
            result = markdown2.markdown(result)

        self.full_result += result

        if br:
            self.full_result += '<br>'
        if new_line:
            self.full_result += '\n'

        utils.push_redis(guid = self.guid, product_id = self.product_id, info = self.full_result, type = type)

    # 提取商品的基本信息
    def analysis_item_info(self):
        pass

    # 分析购买渠道并生成柱状图
    def analysis_buy_channel(self):
        self.record_result('正在分析商品的购买渠道占比...', color = 'black', font_size = 24, strong = True)
        super(RealTimeAnalysis, self).analysis_buy_channel()

    # 分析购买的商品颜色
    def analysis_color(self):
        self.record_result('正在分析该商品不同颜色的购买量...', color = 'black', font_size = 24, strong = True)
        super(RealTimeAnalysis, self).analysis_color()

    # 分析购买的商品大小分类
    def analysis_size(self):
        self.record_result('正在分析该商品不同配置的购买量...', color = 'black', font_size = 24, strong = True)
        super(RealTimeAnalysis, self).analysis_size()

    # 分析购买该商品的地域占比
    def analysis_province(self):
        self.record_result('正在分析该商品不同省份的购买量...', color = 'black', font_size = 24, strong = True)
        super(RealTimeAnalysis, self).analysis_province()

    # 分析商品购买、评论和时间关系图
    def analysis_sell_time(self):
        self.record_result('正在分析商品购买、评论和时间关系图...', color = 'black', font_size = 24, strong = True)
        super(RealTimeAnalysis, self).analysis_sell_time()

    # 分析移动端购买占比
    def analysis_mobile(self):
        self.record_result('正在分析移动端购买占比...', color = 'black', font_size = 24, strong = True)
        super(RealTimeAnalysis, self).analysis_mobile()

    # 分析购买后评论的时间分布
    def analysis_buy_days(self):
        self.record_result('正在分析该商品购买后用户评论的时间', color = 'black', font_size = 24, strong = True)
        super(RealTimeAnalysis, self).analysis_buy_days()

    # 分析购买的用户的等级分布
    def analysis_user_level(self):
        self.record_result('正在分析购买该商品用户的等级...', color = 'black', font_size = 24, strong = True)
        super(RealTimeAnalysis, self).analysis_user_level()

    # 分析 24 小时分布
    def analysis_hour(self):
        self.record_result('正在分析用户购买该商品 24 小时占比...', color = 'black', font_size = 24, strong = True)
        super(RealTimeAnalysis, self).analysis_hour()

    def finish(self):
        self.record_result('finish', default = True, br = False)
