#-*- coding: utf-8 -*-

import sys
import chardet
import re
import json
import datetime
import config
import utils
import redis
import time

from scrapy.http.cookies import CookieJar
from scrapy.utils.project import get_project_settings
from scrapy import Spider
from scrapy import Request
from sqlhelper import SqlHelper

reload(sys)
sys.setdefaultencoding('utf-8')


# python manage.py runspider -a url=https://item.jd.com/11478178241.html -a name=jd
class JDItemInfoSpider(Spider):
    name = 'jd_item_info'

    def __init__(self, name = None, **kwargs):
        super(JDItemInfoSpider, self).__init__(name, **kwargs)
        self.url = kwargs.get("url")
        self.guid = kwargs.get('guid', 'guid')
        self.product_id = kwargs.get('product_id')
        # self.url = 'https://item.jd.com/11478178241.html'
        # self.url = 'https://item.jd.com/4142680.html'
        # self.url = 'https://item.jd.com/3133859.html'
        # self.url = 'https://item.jd.com/3995645.html'
        # self.product_id = 3995645
        self.log('product_id:%s' % self.product_id)
        self.item_table = 'item_%s' % self.product_id
        self.urls_key = '%s_urls' % self.product_id

        self.log_dir = 'log/%s' % self.product_id
        self.is_record_page = False

        self.sql = kwargs.get('sql')
        self.red = kwargs.get('red')

        if self.is_record_page:
            utils.make_dir(self.log_dir)

    def start_requests(self):
        yield Request(
                url = self.url,
                headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                    'Host': 'item.jd.com',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:52.0) Gecko/20100101 '
                                  'Firefox/52.0',
                },
                method = 'GET',
                meta = {
                    'dont_merge_cookies': True,
                    'cookiejar': CookieJar(),
                },
                dont_filter = True,
                callback = self.get_comment_count,
        )

    def get_comment_count(self, response):
        self.save_page('%s.html' % self.product_id, response.body)

        name = response.xpath('//div[@class="p-img"]/a/img/@alt').extract_first()
        self.log('name:%s' % name)

        ids = response.xpath('//div[@class="dd"]/div/@data-sku').extract()
        item_ids = ','.join(ids)
        self.log('item_ids:%s' % item_ids)

        pattern = re.compile('commentVersion:\'(\d+)\'', re.S)
        comment_version = re.search(pattern, response.body).group(1)

        # sort type 5:推荐排序 6:时间排序
        url = 'https://club.jd.com/comment/productPageComments.action?callback=fetchJSON_comment98vv' \
              '{comment_version}&productId={product_id}&score=0&sortType={sort_type}&page=0&pageSize=10' \
              '&isShadowSku=0'. \
            format(product_id = self.product_id, comment_version = comment_version, sort_type = '6')

        yield Request(
                url = url,
                headers = {
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                    'Host': 'club.jd.com',
                    'Referer': 'https://item.jd.com/%s.html' % self.product_id,
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:52.0) Gecko/20100101 '
                                  'Firefox/52.0',
                },
                method = 'GET',
                meta = {
                    'name': name,
                    'comment_version': comment_version,
                    'item_ids': item_ids
                },
                dont_filter = True,
                callback = self.get_all_comment
        )

    def get_all_comment(self, response):
        self.save_page('%s_all_comment.html' % self.product_id, response.body)

        detect = chardet.detect(response.body)
        encoding = detect.get('encoding', '')
        body = response.body.decode(encoding, 'ignore')
        pattern = re.compile('\((.*?)\);', re.S)
        item = re.search(pattern, body)
        if item != None and item.group(1) != None:
            data = json.loads(item.group(1))
            # productCommentSummary
            pcs = data.get('productCommentSummary')
            self.product_msg = {
                'id': self.product_id,
                'name': response.meta.get('name'),
                'good_rate_show': pcs.get('goodRateShow'),
                'poor_rate_show': pcs.get('poorRateShow'),
                'average_score': pcs.get('averageScore'),
                'good_count': pcs.get('goodCount'),
                'general_rate': pcs.get('generalRate'),
                'general_count': pcs.get('generalCount'),
                'poor_rate': pcs.get('poorRate'),
                'after_count': pcs.get('afterCount'),
                'good_rate_style': pcs.get('goodRateStyle'),
                'poor_count': pcs.get('poorCount'),
                'poor_rate_style': pcs.get('poorRateStyle'),
                'general_rate_style': pcs.get('generalRateStyle'),
                'comment_count': pcs.get('commentCount'),
                'product_id': pcs.get('productId'),
                'good_rate': pcs.get('goodRate'),
                'general_rate_show': pcs.get('generalRateShow'),
                'url': self.url,
                'item_ids': response.meta.get('item_ids'),
                'save_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            self.sql.insert_json(self.product_msg, config.jd_item_table, commit = True)

            comment_version = response.meta.get('comment_version')
            comment_count = int(pcs.get('commentCount'))

            page_count = comment_count / 10 + (10 if comment_count < 10000 else 100)  # 这里为什么加 10 or 100？

            # 如果存在表，而且 redis 中有数据，则是抓取中断了，不需要重新插入数据
            if self.sql.is_exists(self.item_table):
                if self.red.llen(self.urls_key) > 0:  # 抓取中断了，不需要重新插入数据
                    page_count = 0
                else:  # redis 中没有数据，则比较数据库中的值是否足够，如果不够则重新抓取
                    command = "SELECT COUNT(*) FROM {}".format(self.item_table)
                    (count,) = self.sql.query_one(command, commit = False)
                    self.log('count:%s comment_count:%s' % (count, comment_count))
                    if count < comment_count:  # 如果不够有两种情况，第一是需要完整的重新抓取，第二是只需要抓取一部分
                        if count <= 3000 and comment_count > count:  # 重新抓取,可能是之前抓取过
                            self.log('count <= 3000 and comment_count > count')
                            pass
                        elif comment_count > count:  # 只抓取增量
                            self.log('comment_count > count')
                            page_count = (comment_count - count) / 10 + 1
                    else:
                        page_count = 0

            self.log('page_count:%s' % page_count)
            for i in range(page_count):
                # sort type 5:推荐排序 6:时间排序
                # url = 'https://club.jd.com/comment/productPageComments.action?callback=fetchJSON_comment98vv' \
                #       '{comment_version}&productId={product_id}&score=0&sortType={sort_type}&page={page}&' \
                #       'pageSize=10&isShadowSku=0'. \
                #     format(product_id = self.product_id, comment_version = comment_version, sort_type = '6',
                #            page = i)
                # url = 'https://club.jd.com/comment/productPageComments.action?callback=fetchJSON_comment98vv1157
                # &productId=3133867&score=0&sortType=5&page=12&pageSize=10&isShadowSku=0'

                data = {
                    'product_id': self.product_id,
                    'page': i,
                    'comment_version': comment_version,
                    'sort_type': 6
                }

                self.red.rpush(self.urls_key, json.dumps(data))

    def save_page(self, filename, data):
        if self.is_record_page:
            with open('%s/%s' % (self.log_dir, filename), 'w') as f:
                f.write(data)
                f.close()

    def close(spider, reason):
        if spider.product_msg != None:
            spider.sql.insert_json(spider.product_msg, config.jd_item_table)

        # 事务提交数据
        spider.sql.commit()
