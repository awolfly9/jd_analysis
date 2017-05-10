#-*- coding: utf-8 -*-

import logging
import os
import time
import utils

from scrapy.crawler import CrawlerProcess
from django.core.management.base import BaseCommand, CommandError
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings


# python manage.py runspider -a url=https://item.jd.com/4142680.html -a name=jd
class Command(BaseCommand):
    help = 'run spider'

    def add_arguments(self, parser):
        parser.add_argument('-a', action = 'append', dest = 'spargs', default = [],
                            help = 'set spider argument (may be repeated)')

    #必须实现的方法
    def handle(self, *args, **options):
        spargs = arglist_to_dict(options['spargs'])
        print('spargs:%s' % spargs)
        print os.getcwd()
        runspider(spargs = spargs)


def runspider(spargs):
    url = spargs.get('url')
    name = spargs.get('name', 'jd')
    guid = spargs.get('guid')
    product_id = spargs.get('product_id')

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


def arglist_to_dict(arglist):
    """Convert a list of arguments like ['arg1=val1', 'arg2=val2', ...] to a
    dict
    """
    return dict(x.split('=', 1) for x in arglist)
