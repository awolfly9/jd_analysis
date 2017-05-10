#-*- coding: utf-8 -*-

import json
import logging
import os
import re
import subprocess
import traceback
import time
import datetime
import redis

import config
from jd_analysis import settings
from sqlhelper import SqlHelper


# 自定义的日志输出
def log(msg, level = logging.DEBUG):
    logging.log(level, msg)
    print('%s [%s], msg:%s' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), level, msg))

    # if level == logging.WARNING or level == logging.ERROR:
    #     for line in traceback.format_stack():
    #         print(line.strip())
    #
    #     for line in traceback.format_stack():
    #         logging.log(level, line.strip())


# 服务器使用，清理端口占用
def kill_ports(ports):
    for port in ports:
        log('kill %s start' % port)
        popen = subprocess.Popen('lsof -i:%s' % port, shell = True, stdout = subprocess.PIPE)
        (data, err) = popen.communicate()
        log('data:\n%s  \nerr:\n%s' % (data, err))

        pattern = re.compile(r'\b\d+\b', re.S)
        pids = re.findall(pattern, data)

        log('pids:%s' % str(pids))

        for pid in pids:
            if pid != '' and pid != None:
                try:
                    log('pid:%s' % pid)
                    popen = subprocess.Popen('kill -9 %s' % pid, shell = True, stdout = subprocess.PIPE)
                    (data, err) = popen.communicate()
                    log('data:\n%s  \nerr:\n%s' % (data, err))
                except Exception, e:
                    log('kill_ports exception:%s' % e)

        log('kill %s finish' % port)

    time.sleep(1)


# 创建文件夹
def make_dir(dir):
    log('make dir:%s' % dir)
    if not os.path.exists(dir):
        os.makedirs(dir)


def arglist_to_dict(arglist):
    """Convert a list of arguments like ['arg1=val1', 'arg2=val2', ...] to a
    dict
    """
    return dict(x.split('=', 1) for x in arglist)


def get_visiter_ip(request):
    if request.META.has_key('HTTP_X_FORWARDED_FOR'):
        ip = request.META['HTTP_X_FORWARDED_FOR']
    else:
        ip = request.META['REMOTE_ADDR']

    return ip


def get_save_image_path():
    if settings.DEBUG == False:
        return '%s/media/images' % settings.BASE_DIR
    else:
        return '%s/jd/static/images' % settings.BASE_DIR


def get_image_src(filename):
    if settings.DEBUG == False:
        result = '![](/media/images/%s)' % filename
    else:
        result = '![](/static/images/%s)' % filename

    return result


red = redis.StrictRedis(host = config.redis_host, port = config.redis_part, db = config.redis_db,
                                password = config.redis_pass)
sql = SqlHelper()


def push_redis(guid, product_id, info, type = 'word', save_to_mysql = True):
    data = {
        'id': None,
        'product_id': product_id,
        'info': info,
        'type': type,
        'guid': guid,
        'save_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    if save_to_mysql:
        sql.insert_json(data, config.analysis_item_table, commit = True)

    red.rpush(guid, json.dumps(data))


def create_analysis_table(product_id):
    # 创建分析商品评论结果表
    command = (
        "CREATE TABLE IF NOT EXISTS {} ("
        "`id` INT(5) NOT NULL AUTO_INCREMENT,"  # 自增 id
        "`product_id` BIGINT(15) DEFAULT NULL ,"  # 商品 id
        "`info` CHAR(255) DEFAULT NULL,"  # 分析结果的信息
        "`type` CHAR(10) DEFAULT NULL,"  # 分析结果类型
        "`guid` CHAR(40) NOT NULL,"  # guid
        "`save_time` TIMESTAMP NOT NULL,"  # 分析数据的时间
        "PRIMARY KEY(id)"
        ") ENGINE=InnoDB".format(config.analysis_item_table + '_' + product_id))
    sql.create_table(command)
