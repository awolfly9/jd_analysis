#-*- coding: utf-8 -*-

import json
import logging
import os
import datetime
import config
import utils
import redis
import sys

from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging
from django.core.management.base import BaseCommand
from sqlhelper import SqlHelper
from jd.models import JDCommentAnalysis
from jd.spiders.jd_comment import JDCommentSpider
from jd.spiders.jd_item_info import JDItemInfoSpider
from scrapy.crawler import CrawlerRunner
from twisted.internet import reactor, defer
from cus_exception import CusException
from jd.analysis_jd_item import Analysis
from jd.send_email import send_email


# python manage.py run_analysis
class Command(BaseCommand):
    help = 'run analysis'

    def add_arguments(self, parser):
        parser.add_argument('-a', action = 'append', dest = 'spargs', default = [],
                            help = 'set spider argument (may be repeated)')

    #必须实现的方法
    def handle(self, *args, **options):
        reload(sys)
        sys.setdefaultencoding('utf-8')

        spargs = utils.arglist_to_dict(options['spargs'])
        key = spargs.get('key', 'running')
        os.chdir(sys.path[0])

        red = redis.StrictRedis(host = config.redis_host, port = config.redis_part, db = config.redis_db,
                                password = config.redis_pass)
        run = red.get(key)
        if run != None:  # 如果有正在运行的进程则等待
            print('have running waiting time:%s' % str(datetime.datetime.now()))
            return

        count = red.llen('analysis_users')
        if count <= 0:  # 如果 redis 中没有需要查询的数据
            print('not data waiting time:%s' % str(datetime.datetime.now()))
            return

        user = red.lpop('analysis_users')
        red.set(key, user)
        print('running... user:%s' % user)
        info = json.loads(user)
        try:
            run_als = RunAnalysis(red, key, user)
            run_als.run()
        except CusException, e:
            info['name'] = e.name
            info['error_msg'] = e.error_msg
            red.lpush('retry_list', info)
        except Exception, e:
            info['name'] = 'unknown'
            info['error_msg'] = e
            logging.exception('RunAnalysis Exception msg:%s' % e)
            red.lpush('retry_list', info)
        finally:
            red.delete(key)

        print ('finish time:%s' % datetime.datetime.now())


class RunAnalysis(object):
    def __init__(self, red, key, user):
        self.key = key
        self.red = red

        data = json.loads(user)
        self.product_id = data.get('product_id')
        self.url = data.get('url')
        self.email = data.get('email')
        self.guid = data.get('guid')
        self.spider_name = 'jd_comment'
        self.spargs = data

        self.sql = SqlHelper()
        self.spargs['red'] = self.red
        self.spargs['sql'] = self.sql

        if not os.path.exists('log'):
            os.makedirs('log')

        configure_logging(install_root_handler = False)
        logging.basicConfig(
                filename = 'log/%s.log' % self.product_id,
                format = '%(levelname)s %(asctime)s: %(message)s',
                level = logging.DEBUG
        )

    def run(self):
        self.runspider()
        self.analysis()
        self.send_notice()
        self.clear_cache()

    # 运行抓取程序，使用代理抓取所有的商品评价
    def runspider(self):
        configure_logging(install_root_handler = False)
        s = get_project_settings()
        runner = CrawlerRunner(settings = s)

        @defer.inlineCallbacks
        def crawl(**spargs):
            yield runner.crawl(JDItemInfoSpider, **spargs)
            yield runner.crawl(JDCommentSpider, **spargs)
            reactor.stop()

        crawl(**self.spargs)
        reactor.run()  # the script will block here until the last crawl call is finished

    # 调度分析
    def analysis(self):
        analysis = Analysis(**self.spargs)
        result = analysis.run()

        jd_comment = JDCommentAnalysis(id = None, guid = self.guid, product_id = self.product_id, item_name = 'name',
                                       content = result, email = self.email, create_time = datetime.datetime.now())
        jd_comment.save()

    # 向用户预留邮箱发送邮件
    def send_notice(self):
        subject = '京东商城 - 商品评价分析结果展示'

        blog_url = '%sjd/full_result/%s' % ('http://127.0.0.1:8000/', self.guid)

        command = "SELECT name FROM {0} WHERE id={1}".format(config.jd_item_table, self.product_id)
        (item_name,) = self.sql.query_one(command)

        body = '''
        您好~
        您订阅的京东商城商品评价信息分析服务已经完成。商品名称:{item_name}，商品链接:{jd_url}，分析结果请见:{blog_url}
        '''.format(jd_url = self.url, blog_url = blog_url, item_name = item_name)

        send_email(to_email = self.email, subject = subject, body = body)

    def clear_cache(self):
        data = self.red.delete(self.key)
        logging.debug('clear_cacha data:%s' % data)
