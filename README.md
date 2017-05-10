# 京东商城商品评价数据分析
附上使用地址
体验地址：<http://awolfly9.com/jd/>
体验示例地址：<http://awolfly9.com/article/jd_comment_analysis>

## 项目来源
互联网购物现在已经是非常普遍的购物方式，在互联网上购买商品并且使用之后，很多人都会回过头来对自己购买的商品进行一些评价，以此来表达自己对于该商品使用后的看法。商品评价的好坏对于一个商品的重要性显而易见，大部分消费者都以此作为快速评判该商品质量优劣的方式。所以，与此同时，有些商家为了获得好评，还会做一些 "好评优惠" 或者 "返点" 活动来刺激消费者评价商品。<br>
既然商品评价对于消费者选购商品而言至关重要，那么我想试试可以从这些评价信息中获取到怎样的价值，来帮助消费者快速获取到关于该商品的一些重要信息，给他们的购物带来更加可靠地保证？<br>
所以，我认为,一种快速、全面、高提炼度和高对比度的信息获取和展示方式将会非常必要。 于是，我采用分布式快速抓取京东的评价信息，然后使用 pandas 对抓取到的数据进行分析。


## 项目依赖
* python 2.7.12
* Django
* django-crontab
* scrapy   
* requests
* pymysql
* pandas
* numpy
* matplotlib
* wordcloud
* Markdown2
* redis 数据库
* mysql 数据库


安装命令：

```
$ pip install Django django-crontab Scrapy requests pymysql pandas numpy wordcloud Markdown2 
```
安装 matplotlib 请参考：[matplotlib github](https://github.com/ehmatthes/pcc/blob/master/chapter_15/README.md#installing-matplotlib)

## 克隆使用
将项目克隆到本地

```
$ git clone https://github.com/awolfly9/jd_analysis.git
```

进入工程目录

```
$ cd jd_analysis
```

创建 Django 使用的数据库

```
$ create database jd_analysis default character set utf8;
```

修改 Django 配置

```
$ vim jd_analysis/settings.py
----------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'jd_analysis',
        'USER': 'root',
        'PASSWORD': '123456',
        'HOST': '',
        'PORT': '',
    }
}
```

修改配置文件中连接数据库配置

```
$ vim config.py
----------
# local
database_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'charset': 'utf8',
}
```

修改 redis 的连接用户名和密码

```
$ vim config.py
----------
redis_pass = ''
redis_host = 'localhost'
redis_part = '6379'
redis_db = 10
```

部分设置参数说明：

| param | Description | 默认值 |
| ----| ---- | ---- | ----|
| is_distributed | 是否分布式抓取 | False |
| is_proxy | 是否使用代理 | False |
| proxy_address | 代理地址 | <http://127.0.0.1:8000/>|
| email_type | 使用哪个邮箱发送邮件 | gmail |
| self_email | 邮箱地址 | 填写自己的邮箱地址 |
| self_password | 邮箱密码 | 填写自己的邮箱密码 |


生成 Django 数据库

```
$ python manage.py makemigrations
$ python manage.py migrate
```

运行 Django 服务器

```
$ python manage.py runserver
```

在浏览器中访问 <http://127.0.0.1:8000/jd/> 进行测试


## 项目说明
完整流程介绍，请见
<http://awolfly9.com/article/jd_comment_full_doc>

如果在使用过程中有任何问题，欢迎提 Issues，也可联系我的微信进入微信群和大伙一起学习。（在我博客中可以找到我的微信）






