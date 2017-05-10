#-*- coding: utf-8 -*-

import logging
import requests
import json
import time
import utils
import config


class ProxyManager(object):
    def __init__(self):
        self.proxy_key = 'proxies'

        self.address = config.proxy_address
        self.db_name = 'jd'
        self.update_time = 0

        self.red = None

    def update_proxy(self, count = 100):
        try:
            r = requests.get(url = '%sselect?name=%s&order=save_time&sort=desc&count=%s' %
                                   (self.address, self.db_name, count), timeout = 20)
            data = json.loads(r.text)
            for item in data:
                proxy = 'http://%s:%s' % (item.get('ip'), item.get('port'))
                self.red.rpush(self.proxy_key, proxy)

            self.update_time = time.time()
            utils.log('*****************proxy manager  proxys:****************\n%s' % (r.text))
        except Exception, e:
            logging.exception('proxymanager update_proxy msg:%s' % e)

    def push_proxy(self, proxy):
        self.red.rpush(self.proxy_key, proxy)

    def get_proxy(self):
        if self.red.llen(self.proxy_key) <= 10:
            self.update_proxy()

        # 十分钟换一拨 IP
        if time.time() - self.update_time >= 600:
            self.update_proxy(count = 50)

        proxy = self.red.lpop(self.proxy_key)
        return proxy

    def delete_proxy(self, proxy):
        try:
            rets = proxy.split(':')
            ip = rets[1]
            ip = ip[2:]

            utils.log('--------------delete ip:%s-----------' % ip)
            r = requests.get(url = '%sdelete?name=%s&ip=%s' % (self.address, self.db_name, ip))
            return r.text
        except:
            return False


proxymng = ProxyManager()
