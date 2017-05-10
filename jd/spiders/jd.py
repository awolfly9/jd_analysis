#-*- coding: utf-8 -*-

import sys
import chardet
import re
import json
import datetime
import config
import utils
import time

from scrapy.http.cookies import CookieJar
from scrapy.utils.project import get_project_settings
from scrapy import Spider
from scrapy import Request

reload(sys)
sys.setdefaultencoding('utf-8')


class JDSpider(Spider):
    name = 'jd'

    def __init__(self, name = None, **kwargs):
        super(JDSpider, self).__init__(name, **kwargs)
        self.url = kwargs.get("url")
        self.guid = kwargs.get('guid', 'guid')
        # self.url = 'https://item.jd.com/11478178241.html'
        # self.url = 'https://item.jd.com/4142680.html'
        # self.url = 'https://item.jd.com/3133859.html'
        pattern = re.compile('\d+', re.S)
        self.product_id = re.search(pattern, self.url).group()
        self.log('product_id:%s' % self.product_id)
        self.item_table = 'item_%s' % self.product_id

        self.log_dir = 'log'
        self.is_record_page = False
        self.sql = kwargs.get('sql')
        self.red = kwargs.get('red')
        self.init()

    def init(self):
        command = (
            "CREATE TABLE IF NOT EXISTS {} ("
            "`id` BIGINT (15) NOT NULL AUTO_INCREMENT,"  # 评论的 id
            "`content` TEXT NOT NULL,"  # 评论的内容
            "`creation_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"  # 评论创建的时间
            "`reply_count` INT(4) DEFAULT NULL ,"  # 回复数量
            "`score` INT(2) DEFAULT NULL,"  # 评星
            "`useful_vote_count` INT(5) DEFAULT NULL,"  # 其他用户觉得有用的数量
            "`useless_vote_count` INT(4) DEFAULT NULL,"  # 其他用户觉得无用的数量
            "`user_level_id` INT(4) DEFAULT NULL,"  # 评论用户等级的 id
            '`user_province` CHAR(8) DEFAULT NULL,'  # 用户的省份
            '`nickname` CHAR(20) DEFAULT NULL,'  # 评论用户的昵称
            '`product_color` CHAR(50) DEFAULT NULL,'  # 商品的颜色
            "`product_size` CHAR(50) DEFAULT NULL,"  # 商品的大小
            "`user_level_name` CHAR(20) DEFAULT NULL,"  # 评论用户的等级
            "`user_client` INT(5) DEFAULT NULL,"  # 用户评价平台
            "`user_client_show` CHAR(20) DEFAULT NULL,"  # 用户评价平台
            "`is_mobile` INT(3) DEFAULT NULL,"  # 是否是在移动端完成的评价
            "`days` INT(3) DEFAULT NULL,"  # 购买后评论的天数
            "`reference_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"  # 购买的时间
            "`after_days` INT(3) DEFAULT NULL,"  # 购买后再次评论的天数
            "`images_count` INT(3) DEFAULT NULL,"  # 评论总图片的数量
            "`ip` CHAR(20) DEFAULT NULL,"  # 再次评论时的 ip 地址
            "`after_content` TEXT DEFAULT NULL,"  # 再次评论的内容
            "`save_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"  # 抓取数据的时间
            "PRIMARY KEY(id)"
            ") ENGINE=InnoDB".format(self.item_table))
        self.sql.create_table(command)

        utils.push_redis(self.guid, self.product_id, '开始抓取京东商城该商品的评价信息...')

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
                callback = self.get_comment_count
        )

    def get_comment_count(self, response):
        self.save_page('%s.html' % self.product_id, response.body)

        name = response.xpath('//head/title/text()').extract_first()
        self.log('name:%s' % name)

        utils.push_redis(self.guid, self.product_id,
                         '商品名称：%s 链接：<a href="%s" target="_blank">%s' % (name, self.url, self.url))

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
                    'item_ids': item_ids,
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

            info = '京东商城显示的评价信息，<strong style="color: red; font-size: 24px;">总的评价数:{comment_count}、好评数:{good_count}、' \
                   '好评百分比:{good_rate}%、中评数:{general_count}、中评百分比:{general_rate}%、差评数:{poor_count}、差评百分比:{poor_rate}% ' \
                   '</strong>' \
                .format(comment_count = pcs.get('commentCount'), good_count = pcs.get('goodCount'),
                        general_count = pcs.get('generalCount'), poor_count = pcs.get('poorCount'),
                        good_rate = pcs.get('goodRate', 0) * 100,
                        general_rate = pcs.get('generalRate', 0) * 100,
                        poor_rate = pcs.get('poorRate', 0) * 100)

            utils.push_redis(self.guid, self.product_id, info)
            # 显示正在加载图片
            utils.push_redis(self.guid, self.product_id,
                             '<li id="loader"><img src="/static/loader.gif"  height="90" width="90"></li>',
                             type = 'image', save_to_mysql = False)

            comment_version = response.meta.get('comment_version')
            comment_count = pcs.get('commentCount')
            page_count = int(comment_count) / 10 + 10  # 这里为什么加 10 ？

            inner_crawl_page = get_project_settings().get('INNER_CRAWL_PAGE', 20)
            if page_count > inner_crawl_page and config.is_distributed:
                for i in range(inner_crawl_page, page_count):
                    # 将数据插入 redis ，实现分布式抓取
                    data = {
                        'prodyct_id': self.product_id,
                        'comment_version': comment_version,
                        'sort_type': '6',
                        'page': i
                    }
                    self.red.rpush(self.product_id, json.dumps(data))

                count = self.red.llen('spiders')
                self.red.set('%s_page' % self.product_id, page_count - inner_crawl_page)
                for i in range(count):
                    guid = self.red.lindex('spiders', i)
                    self.red.rpush(guid, self.product_id)

            # 正常抓取
            count = min(page_count, inner_crawl_page)
            for i in range(count):
                # sort type 5:推荐排序 6:时间排序
                url = 'https://club.jd.com/comment/productPageComments.action?callback=fetchJSON_comment98vv' \
                      '{comment_version}&productId={product_id}&score=0&sortType={sort_type}&page={page}&' \
                      'pageSize=10&isShadowSku=0'. \
                    format(product_id = self.product_id, comment_version = comment_version, sort_type = '6',
                           page = i)

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
                            'page': i,
                            'name': response.meta.get('name'),
                        },
                        dont_filter = True,
                        callback = self.parse_comment
                )

    def parse_comment(self, response):
        self.save_page('%s_%s.html' % (self.product_id, response.meta.get('page')), response.body)

        detect = chardet.detect(response.body)
        encoding = detect.get('encoding', '')
        body = response.body.decode(encoding, 'ignore')

        pattern = re.compile('\((.*?)\);', re.S)
        item = re.search(pattern, body)
        if item != None and item.group(1) != None:
            data = json.loads(item.group(1))
            comments = data.get('comments', [])
            for comment in comments:
                id = comment.get('id')  # 评论的 id
                content = comment.get('content')  # 评论的内容
                creation_time = comment.get('creationTime', '')  # 评论创建的时间
                reply_count = comment.get('replyCount', '')  # 回复数量
                score = comment.get('score', '')  # 评星
                useful_vote_count = comment.get('usefulVoteCount', '')  # 其他用户觉得有用的数量
                useless_vote_count = comment.get('uselessVoteCount', '')  # 其他用户觉得无用的数量
                user_level_id = comment.get('userLevelId', '')  # 评论用户等级的 id
                user_province = comment.get('userProvince', '')  # 用户的省份
                nickname = comment.get('nickname', '')  # 评论用户的昵称
                product_color = comment.get('productColor', '')  # 商品的颜色
                product_size = comment.get('productSize', '')  # 商品的大小
                user_level_name = comment.get('userLevelName', '')  # 评论用户的等级
                user_client = comment.get('userClient', '')  # 用户评价平台
                user_client_show = comment.get('userClientShow', '')  # 用户评价平台
                is_mobile = comment.get('isMobile', '')  # 是否是在移动端完成的评价
                days = comment.get('days', '')  # 购买后评论的天数
                reference_time = comment.get('referenceTime', '')  # 购买的时间
                after_days = comment.get('afterDays', '')  # 购买后再次评论的天数
                images_count = len(comment.get('images', []))  # 评论总图片的数量
                after_user_comment = comment.get('afterUserComment', '')
                if after_user_comment != '' and after_user_comment != None:
                    ip = after_user_comment.get('ip', '')  # 再次评论的 ip 地址

                    h_after_user_comment = after_user_comment.get('hAfterUserComment', '')
                    after_content = h_after_user_comment.get('content', '')  # 再次评论的内容
                else:
                    ip = ''
                    after_content = ''

                content = content.replace('\'', '')
                after_content = after_content.replace('\'', '')

                msg = {
                    'id': id,
                    'content': content,
                    'creation_time': creation_time,
                    'reply_count': reply_count,
                    'score': score,
                    'useful_vote_count': useful_vote_count,
                    'useless_vote_count': useless_vote_count,
                    'user_level_id': user_level_id,
                    'user_province': user_province,
                    'nickname': nickname,
                    'product_color': product_color,
                    'product_size': product_size,
                    'user_level_name': user_level_name,
                    'user_client': user_client,
                    'user_client_show': user_client_show,
                    'is_mobile': is_mobile,
                    'days': days,
                    'reference_time': reference_time,
                    'after_days': after_days,
                    'images_count': images_count,
                    'ip': ip,
                    'after_content': after_content,
                    'save_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }

                self.sql.insert_json(msg, self.item_table)

    def save_page(self, filename, data):
        if self.is_record_page:
            with open('%s/%s' % (self.log_dir, filename), 'w') as f:
                f.write(data)
                f.close()

    def close(spider, reason):
        if spider.product_msg != None:
            spider.sql.insert_json(spider.product_msg, config.jd_item_table)

        # 如果是分布式抓取 清理 redis
        if config.is_distributed:
            utils.red.delete('%s_page' % spider.product_id)
            utils.red.delete(spider.product_id)
            spider.log('clear redis product_id:%s' % spider.product_id)

            # 等其他抓取进程一下
            time.sleep(5)

        command = "SELECT COUNT(*) FROM {}".format('item_%s' % spider.product_id)
        spider.sql.execute(command, commit = False)
        (count,) = spider.sql.cursor.fetchone()

        command = "SELECT COUNT(*) FROM {} WHERE score=5".format('item_%s' % spider.product_id)
        spider.sql.execute(command, commit = False)
        (good_count,) = spider.sql.cursor.fetchone()

        command = "SELECT COUNT(*) FROM {} WHERE score>=3 and score <=4".format('item_%s' % spider.product_id)
        spider.sql.execute(command, commit = False)
        (general_count,) = spider.sql.cursor.fetchone()

        command = "SELECT COUNT(*) FROM {} WHERE score<=2".format('item_%s' % spider.product_id)
        spider.sql.execute(command, commit = False)
        (poor_count,) = spider.sql.cursor.fetchone()

        utils.push_redis(spider.guid, spider.product_id,
                         info = '抓取信息完成，实际抓取评价信息，<strong style="color: red; font-size: 24px;">总共抓取评价数:%s、好评数:%s、'
                                '中评数:%s、差评数:%s</strong>' % (count, good_count, general_count, poor_count))

        # 事务提交数据
        spider.sql.commit()
