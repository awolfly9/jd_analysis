#-*- coding: utf-8 -*-

import matplotlib
import logging
import utils
import config
import numpy as np

matplotlib.use('Agg')

import matplotlib.pyplot as plt

from wordcloud import WordCloud
from matplotlib import font_manager
from pandas import DataFrame, Series
from jd_analysis import settings
from PIL import Image
from cus_exception import CusException


# 注意考虑到多个商品对比的情况
class Analysis(object):
    def __init__(self, **kwargs):
        self.sql = kwargs.get('sql')
        self.guid = kwargs.get('guid')
        self.product_id = kwargs.get('product_id')
        self.url = kwargs.get('url')
        # self.product_id = '3995645'
        # self.product_id = '10213303572'
        self.font_name = 'DroidSansFallback.ttf'
        self.font_path = '%s/font/%s' % (settings.BASE_DIR, self.font_name)

        self.full_result = ''

        self.bar_width = 0.45
        self.opacity = 0.4
        self.color = 'b'

        self.data_frame = None
        self.init()

    def init(self):
        prop = font_manager.FontProperties(fname = self.font_path)
        matplotlib.rcParams['font.family'] = prop.get_name()

        try:
            command = "SELECT product_color, product_size, user_level_name, user_province, reference_time, " \
                      "creation_time,is_mobile, user_client_show, days, user_level_name FROM {0}". \
                format('item_%s' % self.product_id)

            result = self.sql.query(command, commit = False, cursor_type = 'dict')
            self.data_frame = DataFrame(result)
        except Exception, e:
            logging.exception('analysis init exception msg:%s' % e)
            raise CusException('analysis_init', 'analysis_init error:%s' % e)

    def run(self):
        table_name = '%s_%s' % (config.jd_item_table, self.product_id)
        if self.sql.is_exists(table_name) == False:
            self.record_result('出现错误。错误原因：表不存在', strong = True, color = 'red', font_size = 24)
            return self.finish()

        command = 'SELECT count(*) FROM {}'.format(table_name)
        (count,) = self.sql.query_one(command)
        if count <= 0:
            self.record_result('出现错误。错误原因：表为空，没有数据', strong = True, color = 'red', font_size = 24)
            return self.finish()

        try:
            self.analysis_item_info()
            self.analysis_comment_info()
            self.analysis_color()
            self.analysis_size()
            self.analysis_sell_time()
            self.analysis_hour()
            self.analysis_province()
            self.analysis_buy_channel()
            self.analysis_mobile()
            self.analysis_buy_days()
            self.analysis_user_level()
        except Exception, e:
            self.record_result('出现错误。错误原因:%s' % e)
            logging.exception('analysis run exception msg:%s' % e)
            raise CusException('analysis_run', 'analysis_run error:%s' % e)

        self.finish()
        return self.full_result

    def record_result(self, result, color = 'default', font_size = 16, strong = False, type = 'word',
                      br = True, default = False, new_line = False):
        if type == 'word' and default == False:
            if strong:
                result = '<strong style="color: %s; font-size: %spx;">%s</strong>' % (color, font_size, result)
            else:
                result = '<span style="color: %s; font-size: %spx;">%s</span>' % (color, font_size, result)
        elif type == 'image':
            pass

        self.full_result += result

        if br:
            self.full_result += '<br>'
        if new_line:
            self.full_result += '\n'

    def finish(self):
        self.record_result('完成分析', type = 'word', color = 'red', font_size = 24, strong = True)

    # 提取商品的基本信息
    def analysis_item_info(self):
        command = "SELECT name FROM {0} WHERE id={1}".format(config.jd_item_table, self.product_id)
        (item_name,) = self.sql.query_one(command)

        # 商品名称
        self.record_result('# 京东商城商品评价数据分析结果展示\n', default = True, br = False)

        # 商品链接
        self.record_result('京东商品名称：%s \n链接：<a href="%s" target="_blank">%s</a><br>' % (item_name, self.url, self.url),
                           default = True, new_line = True)

        # 评价数量
        command = "SELECT COUNT(*) FROM {}".format('item_%s' % self.product_id)
        (count,) = self.sql.query_one(command, commit = False)

        command = "SELECT COUNT(*) FROM {} WHERE score=5".format('item_%s' % self.product_id)
        (good_count,) = self.sql.query_one(command, commit = False)

        command = "SELECT COUNT(*) FROM {} WHERE score>=3 and score <=4".format('item_%s' % self.product_id)
        (general_count,) = self.sql.query_one(command, commit = False)

        command = "SELECT COUNT(*) FROM {} WHERE score<=2".format('item_%s' % self.product_id)
        (poor_count,) = self.sql.query_one(command, commit = False)

        info = '总共获取评价数:%s、好评数:%s、中评数:%s、差评数:%s' % (count, good_count, general_count, poor_count)
        self.record_result(result = info, color = 'red', font_size = 24, strong = True)

        # 百分比
        info = '好评比例:%.2f%%、中评好评比例:%.2f%%、差评好评比例:%.2f%%' % (
            good_count * 1.0 / count * 100, general_count * 1.0 / count * 100, poor_count * 1.0 / count * 100)
        self.record_result(result = info, color = 'red', font_size = 24, strong = True, new_line = True)
        self.record_result(result = '\n')

    # 分析评论，获取评论关键词
    def analysis_comment_info(self):
        self.good_comment()
        self.general_comment()
        self.poor_comment()

    # 分析好评数据
    def good_comment(self):
        command = "SELECT content FROM {0} WHERE score = 5".format('item_%s' % self.product_id)
        result = self.sql.query(command)
        text = ''
        for res in result:
            text += res[0]

        self.analysis_content(text, 'good')

    # 分析中评数据
    def general_comment(self):
        command = "SELECT content FROM {0} WHERE score=3 or score=4".format('item_%s' % self.product_id)
        result = self.sql.query(command)
        text = ''
        for res in result:
            text += res[0]

        self.analysis_content(text, 'general')

    # 分析差评数据
    def poor_comment(self):
        command = "SELECT content FROM {0} WHERE score<3".format('item_%s' % self.product_id)
        result = self.sql.query(command)
        text = ''
        for res in result:
            text = text + res[0]

        self.analysis_content(text, 'poor')

    # 生成词云
    def analysis_content(self, contents, type):
        # 解决京东的评价中包含 &hellip
        contents = contents.replace('&hellip', '')
        if contents == '':
            return

        d = '%s/media/mask.png' % settings.BASE_DIR
        mask = np.array(Image.open(d))
        wordcloud = WordCloud(font_path = self.font_path, mask = mask).generate(contents)

        result = ''
        for i, ((word, count), font_size, position, orientation, color) in enumerate(wordcloud.layout_):
            if i <= 3:
                result += word + '、'

        if type == 'good':
            result = '好评数据 关键字：%s' % result
        elif type == 'general':
            result = '中评数据 关键字：%s' % result
        elif type == 'poor':
            result = '差评数据 关键字：%s' % result

        self.record_result(result, strong = True, color = 'black', font_size = 24)

        filename = '%s_%s.png' % (self.product_id, type)
        wordcloud.to_image().save('%s/%s' % (utils.get_save_image_path(), filename))

        result = utils.get_image_src(filename = filename)
        self.record_result(result, type = 'image')

    # 分析购买渠道并生成柱状图
    def analysis_buy_channel(self):
        # self.record_result('用户购买该商品使用的客户端', color = 'black', font_size = 24, strong = True)

        obj = self.data_frame['user_client_show']
        obj = obj.value_counts()
        obj = obj.rename({u'': u'其他，网页端'})
        # obj = obj.append(mobile_obj)
        # obj.plot(style = 'ro-')
        ax = obj.plot(kind = 'bar', alpha = self.opacity, color = self.color)
        ax.set_xticklabels(obj.index, rotation = 45 if len(obj.index) > 3 else 0)

        # 显示柱状图的百分比
        count = obj.sum()
        for i, val in enumerate(obj.values):
            ax.text(i - 0.25, val, '%.3f%%' % (val * 1.0 / count * 100))

        # 尝试将购买渠道和在移动端购买放到一个图中
        # plt.subplot(111)
        # obj = self.data_frame['is_mobile']
        # obj = obj.value_counts()
        #
        # obj = obj.rename({1: '移动端', 0: 'PC'})
        # plt.pie(x = obj.values, autopct = '%.0f%%', radius = 0.3, labels = obj.index)

        plt.title('该商品不同客户端的购买数量关系图')
        ax.set_xlabel('客户端')
        ax.set_ylabel('数量')

        filename = '%s_channel.png' % self.product_id
        plt.tight_layout()
        plt.savefig('%s/%s' % (utils.get_save_image_path(), filename))
        plt.clf()
        result = utils.get_image_src(filename = filename)
        self.record_result(result, type = 'image')

    # 分析购买的商品颜色
    def analysis_color(self):
        # self.record_result('用户购买该商品不同颜色比例', color = 'black', font_size = 24, strong = True)

        obj = self.data_frame['product_color']
        obj = obj.value_counts()

        plt.title('该商品不同颜色购买数量关系图')
        ax = plt.subplot(111)
        ax.set_xlabel('颜色')
        ax.set_ylabel('数量')

        obj = obj.rename({'': u'其他'})
        ax = obj.plot(kind = 'bar', alpha = self.opacity, color = self.color)

        # 是否倾斜显示 X 轴标签
        if len(ax.containers) > 0:
            if len(obj.index) > 5:
                xticks_pos = [1 * patch.get_width() + patch.get_xy()[0] for patch in ax.containers[0]]
                plt.xticks(xticks_pos, obj.index, rotation = 45, ha = 'right')
            else:
                xticks_pos = [0.5 * patch.get_width() + patch.get_xy()[0] for patch in ax.containers[0]]
                plt.xticks(xticks_pos, obj.index, rotation = 0)

        # 显示柱状图的百分比
        count = obj.sum()
        for i, val in enumerate(obj.values):
            ax.text(i - 0.25, val, '%.3f%%' % (val * 1.0 / count * 100))

        plt.tight_layout()
        filename = '%s_color.png' % self.product_id
        plt.savefig('%s/%s' % (utils.get_save_image_path(), filename))
        plt.clf()
        result = utils.get_image_src(filename = filename)
        self.record_result(result, type = 'image')

    # 分析购买的商品大小分类
    def analysis_size(self):
        # self.record_result('用户购买该商品不同配置比例', color = 'black', font_size = 24, strong = True)

        obj = self.data_frame['product_size']
        obj = obj.value_counts()

        plt.title('该商品不同配置购买数量关系图')
        ax = plt.subplot(111)
        ax.set_xlabel('配置')
        ax.set_ylabel('数量')

        obj = obj.rename({'': u'其他'})
        ax = obj.plot(kind = 'bar', alpha = self.opacity, color = self.color, rot = 0)

        # 是否倾斜显示 X 轴标签
        if len(ax.containers) > 0:
            if len(obj.index) > 5:
                xticks_pos = [1 * patch.get_width() + patch.get_xy()[0] for patch in ax.containers[0]]
                plt.xticks(xticks_pos, obj.index, rotation = 45, ha = 'right')
            else:
                xticks_pos = [0.5 * patch.get_width() + patch.get_xy()[0] for patch in ax.containers[0]]
                plt.xticks(xticks_pos, obj.index, rotation = 0)

        # 显示柱状图的百分比
        count = obj.sum()
        for i, val in enumerate(obj.values):
            ax.text(i - 0.25, val, '%.3f%%' % (val * 1.0 / count * 100))

        plt.tight_layout()
        filename = '%s_size.png' % self.product_id
        plt.savefig('%s/%s' % (utils.get_save_image_path(), filename))
        plt.clf()
        result = utils.get_image_src(filename = filename)
        self.record_result(result, type = 'image')

    # 分析购买该商品的地域占比
    def analysis_province(self):
        # self.record_result('该商品在各省的销量比例', color = 'black', font_size = 24, strong = True)

        obj = self.data_frame['user_province']
        obj = obj.value_counts()

        plt.title('该商品不同省份购买数量关系图')
        ax = plt.subplot(111)
        ax.set_xlabel('省份名称')
        ax.set_ylabel('数量')

        obj = obj.rename({'': u'未知'})
        ax = obj.plot(kind = 'bar', alpha = self.opacity, color = self.color, rot = 0)

        # 是否倾斜显示 X 轴标签
        if len(ax.containers) > 0:
            if len(obj.index) > 5:
                xticks_pos = [1 * patch.get_width() + patch.get_xy()[0] for patch in ax.containers[0]]
                plt.xticks(xticks_pos, obj.index, rotation = 45, ha = 'right')
            else:
                xticks_pos = [0.5 * patch.get_width() + patch.get_xy()[0] for patch in ax.containers[0]]
                plt.xticks(xticks_pos, obj.index, rotation = 0)

        # 显示柱状图的百分比
        count = obj.sum()
        for i, val in enumerate(obj.values):
            if i <= 5:
                ax.text(i - 0.25, val, '%.3f%%' % (val * 1.0 / count * 100))

        plt.tight_layout()
        filename = '%s_province.png' % self.product_id
        plt.savefig('%s/%s' % (utils.get_save_image_path(), filename))
        plt.clf()
        result = utils.get_image_src(filename = filename)
        self.record_result(result, type = 'image')

    # 分析购买该商品的地域占比
    # def analysis_province_no_other(self):
    #     self.record_result('正在分析该商品不同省份的购买量', color = 'black', font_size = 24, strong = True)
    #
    #     obj = self.data_frame['user_province']
    #     obj = obj.value_counts()
    #
    #     plt.title('商品不同省份的购买量')
    #     ax = plt.subplot(111)
    #     ax.set_xlabel('购物省份名称')
    #     ax.set_ylabel('购物数量')
    #
    #     obj = obj.drop(labels = '')
    #     ax = obj.plot(kind = 'bar', alpha = self.opacity, color = self.color, rot = 0)
    #
    #     # 是否倾斜显示 X 轴标签
    #     if len(ax.containers) > 0:
    #         if len(obj.index) > 5:
    #             xticks_pos = [1 * patch.get_width() + patch.get_xy()[0] for patch in ax.containers[0]]
    #             plt.xticks(xticks_pos, obj.index, rotation = 45, ha = 'right')
    #         else:
    #             xticks_pos = [0.5 * patch.get_width() + patch.get_xy()[0] for patch in ax.containers[0]]
    #             plt.xticks(xticks_pos, obj.index, rotation = 0)
    #
    #     # 显示柱状图的百分比
    #     count = obj.sum()
    #     for i, val in enumerate(obj.values):
    #         if i <= 5:
    #             ax.text(i - 0.25, val, '%.3f%%' % (val * 1.0 / count * 100))
    #
    #     plt.tight_layout()
    #     filename = '%s_province_no_other.png' % self.product_id
    #     plt.savefig('%s/%s' % (utils.get_save_image_path(), filename))
    #     plt.clf()
    #     result = utils.get_image_src(filename = filename)
    #     self.record_result(result)

    # 分析商品购买、评论和时间关系图
    def analysis_sell_time(self):
        # self.record_result('该商品购买时间、评论时间关系图', color = 'black', font_size = 24, strong = True)

        cre_obj = Series(index = self.data_frame['creation_time'], data = 1)
        cre_obj = cre_obj.resample(rule = 'M').sum()
        cre_obj = cre_obj.fillna(0)

        # cre_obj.plot(xticks = cre_obj.index, label = '评论数量', kind = 'line', color = 'orange')
        cre_obj.plot(style = 'o-', xticks = cre_obj.index, label = '评论数量')

        obj = Series(index = self.data_frame['reference_time'], data = 1)
        obj = obj.resample(rule = 'M').sum()
        obj = obj.fillna(0)

        # obj.plot(xticks = obj.index, label = '购买数量')
        ax = obj.plot(style = 'o-', xticks = obj.index, label = '购买数量')
        if len(obj.index) <= 5:
            ax.set_xticklabels([x.strftime('\n%d\n%m\n%Y') for x in obj.index])
        else:
            count = len(obj.index)
            if count <= 10:
                ax.set_xticklabels([x.strftime('\n%d\n%m\n%Y') if i % 2 == 0 else '' for i, x in enumerate(obj.index)])
            else:
                ax.set_xticklabels(
                        [x.strftime('\n%d\n%m\n%Y') if i % 4 == 0 or i == (len(obj.index) - 1) else '' for i, x in
                         enumerate(obj.index)])

        plt.title('该商品购买时间、评论时间关系图')
        ax.set_xlabel('时间')
        ax.set_ylabel('购买/评论数量')

        plt.tight_layout()
        plt.legend()
        filename = '%s_time.png' % self.product_id
        plt.savefig('%s/%s' % (utils.get_save_image_path(), filename))
        plt.clf()

        result = utils.get_image_src(filename = filename)
        self.record_result(result, type = 'image')

    # 分析移动端购买占比
    def analysis_mobile(self):
        # self.record_result('<strong style="color: black; font-size: 24px;">正在分析该商品不同省份的购买量...</strong>')

        fig_size = plt.rcParams["figure.figsize"]
        plt.figure(figsize = (2.4, 2.4))

        obj = self.data_frame['is_mobile']
        obj = obj.value_counts()

        obj = obj.rename({1: '移动端', 0: 'PC'})
        plt.pie(x = obj.values, autopct = '%.0f%%', radius = 0.7, labels = obj.index, startangle = 180)

        plt.title('该商品移动/ PC 购买比例')

        plt.tight_layout()
        filename = '%s_mobile.png' % self.product_id
        plt.savefig('%s/%s' % (utils.get_save_image_path(), filename))
        plt.figure(figsize = fig_size)
        plt.clf()
        result = utils.get_image_src(filename = filename)
        self.record_result(result, type = 'image')

    # 分析购买后评论的时间分布
    def analysis_buy_days(self):
        # self.record_result('<strong style="color: black; font-size: 24px;">正在分析该商品不同省份的购买量...</strong>')

        obj = self.data_frame['days']
        obj = obj.value_counts()
        obj = obj.sort_index()

        # 如果有超过 20 天后评论的，则合并在一起
        if len(obj.index) > 20:
            value = obj[obj.index >= 20].sum()
            obj = obj.drop(obj[obj.index > 20].index)
            obj.values[-1] += value

        ax = obj.plot(kind = 'line', style = 'ro-', xticks = obj.index)
        obj = obj.rename({obj.index[-1]: str(obj.index[-1]) + '+'})
        ax.set_xticklabels(labels = obj.index, rotation = 0)

        count = obj.sum()
        for i, val in enumerate(obj.values):
            if i <= 5:
                ax.text(i - 0.4, val, '%.3f%%' % (val * 1.0 / count * 100))
            if i == len(obj.index) - 1:
                ax.text(i - 0.4, val, '%.3f%%' % (val * 1.0 / count * 100))

        plt.title('该商品用户购买后写下评论的时间关系图')
        ax.set_xlabel('写评论时间（天）')
        ax.set_ylabel('数量')

        plt.tight_layout()
        filename = '%s_days.png' % self.product_id
        plt.savefig('%s/%s' % (utils.get_save_image_path(), filename))
        plt.clf()

        result = utils.get_image_src(filename = filename)
        self.record_result(result, type = 'image')

    # 分析购买的用户的等级分布
    def analysis_user_level(self):
        # self.record_result('<strong style="color: black; font-size: 24px;">正在分析该商品不同省份的购买量...</strong>')

        obj = self.data_frame['user_level_name']
        obj = obj.value_counts()

        ax = obj.plot(kind = 'bar', alpha = self.opacity, color = self.color)
        ax.set_xticklabels(obj.index, rotation = 0 if len(obj.index) <= 6 else 45)

        count = obj.sum()
        for i, val in enumerate(obj.values):
            ax.text(i - 0.25, val, '%.2f%%' % (val * 1.0 / count * 100))

        plt.title('购买该商品的用户等级分布图')
        ax.set_xlabel('用户等级')
        ax.set_ylabel('数量')

        plt.tight_layout()
        filename = '%s_user_level.png' % self.product_id
        plt.savefig('%s/%s' % (utils.get_save_image_path(), filename))
        plt.clf()

        result = utils.get_image_src(filename = filename)
        self.record_result(result, type = 'image')

    # 分析 24 小时分布
    def analysis_hour(self):
        # self.record_result('<strong style="color: black; font-size: 24px;">正在分析该商品不同省份的购买量...</strong>')

        obj = self.data_frame['creation_time']
        obj = obj.dt.hour
        obj = obj.value_counts()
        obj = obj.sort_index()
        index = np.arange(0, 24)
        obj = obj.reindex(index, method = 'ffill', fill_value = 0)

        ax = obj.plot(xticks = index, kind = 'line', style = 'o-', label = '评论数量')

        obj = self.data_frame['reference_time']
        obj = obj.dt.hour
        obj = obj.value_counts()
        obj = obj.sort_index()
        obj = obj.reindex(index, method = 'ffill', fill_value = 0)

        obj.plot(xticks = index, kind = 'line', style = 'o-', label = '购买数量')

        ax.set_ylabel('数量')
        ax.set_xlabel('24 小时分布')
        plt.title('购买/评论该商品的 24 小时时间分布图')

        plt.tight_layout()
        plt.legend()
        filename = '%s_creation_time.png' % self.product_id
        plt.savefig('%s/%s' % (utils.get_save_image_path(), filename))
        plt.clf()

        result = utils.get_image_src(filename = filename)
        self.record_result(result, type = 'image')
