# -*- coding=utf-8 -*-

from __future__ import unicode_literals
from django.db import models


# Create your models here.
class JDVisit(models.Model):
    id = models.AutoField(primary_key = True, name = 'id')
    jd_url = models.CharField(max_length = 200, name = 'jd_url', verbose_name = '京东商城商品的 url 链接', default = '')
    ip = models.CharField(max_length = 20, name = 'ip', verbose_name = '访问者的 IP 地址')
    ip_address = models.CharField(max_length = 200, name = 'ip_address', verbose_name = 'IP 对应的地址', default = None)
    visit_time = models.DateTimeField(name = 'visit_time', verbose_name = '访问的时间')
    user_agent = models.TextField(max_length = 1000, name = 'user_agent', verbose_name = '访问者的 HTTP_USER_AGENT',
                                  default = '')

    ip_hight_success = models.CharField(max_length = 10, name = 'ip_hight_success', verbose_name = '查询 IP 高精度定位是否成功',
                                        default = '')
    ip_hight_address = models.CharField(max_length = 200, name = 'ip_hight_address', verbose_name = 'IP 对应的高精度地址',
                                        default = '')
    ip_confidence = models.FloatField(name = 'ip_confidence', verbose_name = 'IP 高精度查询结果的可信度', default = 0)
    ip_hight_radius = models.IntegerField(name = 'ip_hight_radius', verbose_name = 'IP 高精度查询结果的偏移半径', default = -1)
    ip_hight_lat = models.FloatField(name = 'ip_hight_lat', verbose_name = 'IP 高精度查询经度', default = -1)
    ip_hight_long = models.FloatField(name = 'ip_hight_long', verbose_name = 'IP 高精度查询纬度', default = -1)

    class Meta:
        db_table = 'jd_visit'


# Create your models here.
class AnalysisUser(models.Model):
    id = models.AutoField(primary_key = True, name = 'id')
    url = models.CharField(max_length = 200, name = 'url', verbose_name = '文章 url 地址')
    email = models.EmailField(name = 'email', verbose_name = '用户留下的 email')
    guid = models.CharField(max_length = 100, name = 'guid', verbose_name = 'GUID')
    ip = models.CharField(max_length = 20, name = 'ip', verbose_name = '访问者的 IP 地址')
    product_id = models.CharField(max_length = 100, name = 'product_id', verbose_name = '根据 URL 提取的 id')
    create_time = models.DateTimeField(name = 'create_time', auto_now = True)

    class Meta:
        db_table = 'jd_comment_analysis_user'
        ordering = ['-create_time']


class JDCommentAnalysis(models.Model):
    id = models.AutoField(primary_key = True, name = 'id')
    guid = models.CharField(max_length = 100, name = 'guid', verbose_name = 'GUID')
    email = models.EmailField(max_length = 50, name = 'email', verbose_name = '用户留下的 email', default = '')
    product_id = models.BigIntegerField(name = 'product_id', verbose_name = '京东商品的 id')
    item_name = models.CharField(max_length = 200, name = 'item_name', verbose_name = '京东商城商品的名称')
    content = models.TextField(name = 'content', verbose_name = '完整的分析结果展示')
    create_time = models.DateTimeField(name = 'create_time', auto_now = True)

    class Meta:
        db_table = 'jd_comment_analysis_result'
        ordering = ['-create_time']
