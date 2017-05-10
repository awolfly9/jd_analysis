#-*- coding: utf-8 -*-

import json
import logging
import os
import subprocess
import re
import uuid
import datetime

import markdown2
import redis
from django.db.models import Q

import config
import utils

from django.dispatch import receiver
from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings
from django.views import View

from models import JDCommentAnalysis
from models import AnalysisUser
from sqlhelper import SqlHelper
from django.core.signals import request_finished

red = redis.StrictRedis(host = config.redis_host, port = config.redis_part, db = config.redis_db,
                        password = config.redis_pass)


# Create your views here.
class IndexView(View):
    def get(self, request):
        logging.info('index view')
        return render(request, 'jd_index.html', context = {})


def runspider(request):
    data = {
        'status': 'failure',
        'guid': '0',
        'info': '',
    }

    try:
        # 正式环境用 post 请求
        url = request.POST.get('url')
        force = request.POST.get('force', 'false')
        pattern = re.compile('\d+', re.S)
        product_id = re.search(pattern, url).group()
        sql = SqlHelper()

        utils.log('product_id:%s' % product_id)

        if 'item.jd.com' in url and product_id != None:
            data['status'] = 'success'
            data['guid'] = str(uuid.uuid4())
            data['info'] = '成功接收数据，正在为您抓取并分析数据，精彩稍候呈现',

            command = "SELECT id FROM {table} WHERE id={product_id}". \
                format(table = config.jd_item_table, product_id = product_id)
            result = sql.query_one(command)

            if result == None:
                name = 'jd'
                cmd = 'cd {dir};python manage.py real_time_analysis -a name={name} -a guid={guid} ' \
                      '-a product_id={product_id} -a url={url};'. \
                    format(url = str(url), name = name, dir = settings.BASE_DIR, guid = data.get('guid'),
                           product_id = product_id)

                subprocess.Popen(cmd, shell = True)
            else:
                if force == 'false':
                    utils.log('数据库中存在数据，从数据库中取出分析结果')
                    command = "SELECT * FROM {0} WHERE product_id={1} ORDER BY id". \
                        format(config.analysis_item_table, product_id)
                    result = sql.query(command)
                    for res in result:
                        utils.push_redis(data.get('guid'), res[1], res[2], res[3], save_to_mysql = False)
                else:
                    command = "DELETE FROM {0} WHERE produce_id={1}".format(config.analysis_item_table, product_id)
                    sql.execute(command)
                    #重新分析数据
                    cmd = 'cd {dir};python manage.py analysis -a url={url} -a name={name} -a guid={guid} -a ' \
                          'product_id={product_id};'. \
                        format(url = url, name = 'jd', dir = settings.BASE_DIR, guid = data.get('guid'),
                               product_id = product_id)

                    subprocess.Popen(cmd, shell = True)
        else:
            data['info'] = '传入网址有误，请检查后重新输入,请输入以下格式的网址:\n%s' % 'https://item.jd.com/3995645.html'
    except Exception, e:
        logging.error('run spider exception:%s' % e)
        data['info'] = '出现错误，错误原因：%s' % e

    response = HttpResponse(json.dumps(data), content_type = "application/json")
    response.set_cookie('status', data.get('status'))
    response.set_cookie('guid', data.get('guid'))
    return response


def randitem(request):
    data = {
        'status': 'failure',
        'guid': '0',
        'info': '',
    }
    try:
        is_rand = request.POST.get('rand')
        if is_rand == 'true':
            data['status'] = 'success'
            data['guid'] = str(uuid.uuid4())
            data['info'] = '成功接收数据，正在为您抓取并分析数据，精彩稍候呈现'

            cmd = 'cd {dir};python manage.py rand_item_analysis -a name={name} -a guid={guid}'. \
                format(dir = settings.BASE_DIR, name = 'jd', guid = data.get('guid'))
            subprocess.Popen(cmd, shell = True)
        else:
            data['info'] = '传入参数有误'
    except Exception, e:
        logging.error('rand item exception:%s' % e)
        data['info'] = '出现错误，错误原因：%s' % e

    response = HttpResponse(json.dumps(data), content_type = "application/json")
    response.set_cookie('status', data.get('status'))
    response.set_cookie('guid', data.get('guid'))
    return response


def analysis(request):
    data = {
        'status': 'failure'
    }

    try:
        status = request.COOKIES.get('status', '')
        guid = request.COOKIES.get('guid', '0')
        if status == 'success' and guid != '0':
            msg = red.lpop(guid)
            if msg != None:
                data = json.loads(msg)
                data['status'] = status
                utils.log('info:%s' % data.get('info'))
                response = HttpResponse(json.dumps(data), content_type = "application/json")
                return response
    except Exception, e:
        logging.error('analysis data exception:%s' % e)

    response = HttpResponse(json.dumps(data), content_type = "application/json")
    return response


def register_spider(request):
    data = {}
    try:
        guid = str(uuid.uuid4())
        data['guid'] = guid

        red.lpush('spiders', guid)
    except Exception, e:
        logging.error('register_spider exception:%s' % e)

    response = HttpResponse(json.dumps(data), content_type = "application/json")
    return response


def delete_spider(request):
    data = {
        'result': False
    }
    try:
        guid = request.GET.get('guid', -1)
        print('guid:%s' % guid)
        if guid != -1 and guid != None:
            red.delete(guid)
            red.lrem('spiders', 1, guid)
            data['result'] = True
    except Exception, e:
        logging.error('analysis data exception:%s' % e)

    response = HttpResponse(json.dumps(data), content_type = "application/json")
    return response


#
# @receiver(request_finished)
# def my_callback(sender, **kwargs):
#     print("Request finished!")
#


class FullView(View):
    def get(self, request):
        return render(request, 'full_index.html', context = {})


def full_comment(request):
    data = {
        'status': 'failure',
        'guid': str(uuid.uuid4()),
        'info': '',
    }

    try:
        if request.method == 'POST':
            url = request.POST.get('url')
            email = request.POST.get('email')

            # 检查 url 和 email 符合规范
            if url == None or 'item.jd.com' not in url:
                data['info'] = 'URL 格式不正确，请重新输入'
            elif email == None or email == '' or '@' not in email:
                data['info'] = '邮箱格式不正确，请重新输入'
            else:
                pattern = re.compile('\d+', re.S)
                product_id = re.search(pattern, url).group()

                if 'item.jd.com' in url and product_id != None:
                    user = {
                        'url': url,
                        'product_id': product_id,
                        'email': email,
                        'guid': data.get('guid')
                    }
                    red.rpush('analysis_users', json.dumps(user))

                    user = AnalysisUser(id = None, url = url, email = email, product_id = product_id,
                                        guid = data.get('guid'),
                                        ip = utils.get_visiter_ip(request), create_time = datetime.datetime.now())
                    user.save()

                    data['status'] = 'success'
                    data['info'] = '已经收到信息，正在开始分析'
                else:
                    data['info'] = '输入参数不符合规范，请重新输入'
    except Exception, e:
        data['info'] = '出现错误：%s' % e

    response = HttpResponse(json.dumps(data), content_type = "application/json")
    response.set_cookie('status', data.get('status'))
    response.set_cookie('guid', data.get('guid'))
    return response


class AnalysisResultView(View):
    def get(self, request, param):
        print('path:%s param:%s' % (request.path, param))
        try:
            article = JDCommentAnalysis.objects.filter(Q(guid__iexact = param) | Q(product_id__iexact = param)).first()
            article.content = markdown2.markdown(text = article.content, extras = {
                'tables': True,
                'wiki-tables': True,
                'fenced-code-blocks': True,
            })

            context = {
                'article': article
            }

            return render(request, 'full_result.html', context = context)
        except:
            return render(request, '404.html')
