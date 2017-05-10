#-*- coding: utf-8 -*-

import os
import subprocess
import requests
import config
import utils
import re
import random

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from sqlhelper import SqlHelper


class Command(BaseCommand):
    help = 'randitem'

    def add_arguments(self, parser):
        parser.add_argument('-a', action = 'append', dest = 'spargs', default = [],
                            help = 'set spider argument (may be repeated)')

    #必须实现的方法
    def handle(self, *args, **options):
        spargs = arglist_to_dict(options['spargs'])
        randitem(spargs)


def randitem(spargs):
    guid = spargs.get('guid', 0)
    utils.push_redis(guid, 0, '正在随机产生商品链接', save_to_mysql = False)

    url = 'https://diviner.jd.com/diviner?p=610009&callback=jsonpCallbackMoreGood&lid=1&uuid=122270672' \
          '.1492415671516609876050.1492415672.1492415672.1492415672.1&pin=&lim=100&ec=utf-8&_=1492415813682'
    headers = {
        'Host': 'diviner.jd.com',
        'Referer': 'https://www.jd.com/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:52.0) Gecko/20100101 Firefox/52.0'
    }
    cookies = {
        '__jda': '122270672.1492415671516609876050.1492415672.1492415672.1492415672.1',
        '__jdb': '122270672.1.1492415671516609876050|1.1492415672',
        '__jdc': '122270672',
        '__jdv': '122270672|direct|-|none|-|1492415671524',
        '__jdu': '1492415671516609876050',
    }

    r = requests.get(url = url, headers = headers, cookies = cookies, timeout = 20)
    pattern = re.compile('"sku":(\d+),', re.S)
    ids = re.findall(pattern, r.text)
    id = random.choice(ids)

    url = 'https://item.jd.com/%s.html' % str(id)
    utils.push_redis(guid, 0, '生成商品链接:<a href="%s" target="_blank">%s' % (url, url), save_to_mysql = False)

    sql = SqlHelper()
    command = "SELECT id FROM {table} WHERE id={product_id}". \
        format(table = config.jd_item_table, product_id = id)
    result = sql.query_one(command)

    # 如果数据库中没有，则重新抓取
    if result == None:
        cmd = 'cd {dir};python manage.py real_time_analysis -a name={name} -a guid={guid} ' \
              '-a product_id={product_id} -a url={url};'. \
            format(url = str(url), name = 'jd', dir = settings.BASE_DIR, guid = guid,
                   product_id = id)
        subprocess.Popen(cmd, shell = True)
    else:
        # 如果数据库中存在则，直接读取数据库中数据
        command = "SELECT * FROM {0} WHERE product_id={1} ORDER BY id". \
            format(config.analysis_item_table, id)
        result = sql.query(command)
        for res in result:
            utils.push_redis(guid, res[1], res[2], res[3], save_to_mysql = False)


def arglist_to_dict(arglist):
    """Convert a list of arguments like ['arg1=val1', 'arg2=val2', ...] to a
    dict
    """
    return dict(x.split('=', 1) for x in arglist)
