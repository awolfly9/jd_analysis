#-*- coding: utf-8 -*-
import json
import os
import sys

import datetime
import redis
from django.core.management.base import BaseCommand

# python manage.py run_analysis
import config
import utils


class Command(BaseCommand):
    help = 'clear running'

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
        res = red.get(key)
        if res != None:
            info = json.loads(res)
            info['name'] = 'clear_running'
            info['error_msg'] = 'interrupt error'
            red.lpush('retry_list', info)
            red.delete(key)
