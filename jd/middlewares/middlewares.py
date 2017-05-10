# coding=utf-8

import logging

from twisted.internet import defer
from twisted.internet.error import TimeoutError, DNSLookupError, \
    ConnectionRefusedError, ConnectionDone, ConnectError, \
    ConnectionLost, TCPTimedOutError

from scrapy.exceptions import NotConfigured
from scrapy.utils.response import response_status_message
from scrapy.xlib.tx import ResponseFailed
from scrapy.core.downloader.handlers.http11 import TunnelError
from jd.proxymanager import proxymng

logger = logging.getLogger(__name__)


class ProxyMiddleware(object):
    def process_request(self, request, spider):
        try:
            request.meta['req_count'] = request.meta.get('req_count', 0) + 1

            if request.meta.get('is_proxy', False):
                request.meta['proxy'] = proxymng.get_proxy()
        except Exception, e:
            logging.warning('ProxyMiddleware Exception:%s' % str(e))

    def process_exception(self, request, exception, spider):
        logging.error('process_exception error_request request exception:%s url:%s  proxy:%s' % (
            exception, request.url, str(request.meta)))

        if request.meta.get('is_proxy', False):
            proxymng.delete_proxy(request.meta.get('proxy'))
            request.meta['proxy'] = proxymng.get_proxy()

        return request


class CustomRetryMiddleware(object):
    # IOError is raised by the HttpCompression middleware when trying to
    # decompress an empty response
    EXCEPTIONS_TO_RETRY = (defer.TimeoutError, TimeoutError, DNSLookupError,
                           ConnectionRefusedError, ConnectionDone, ConnectError,
                           ConnectionLost, TCPTimedOutError, ResponseFailed,
                           IOError, TunnelError)

    def __init__(self, settings):
        if not settings.getbool('RETRY_ENABLED'):
            raise NotConfigured
        self.max_retry_times = settings.getint('RETRY_TIMES')
        self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
        # self.priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST')
        self.priority_adjust = 1

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response

        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response
        return response

    def process_exception(self, request, exception, spider):
        if isinstance(exception, self.EXCEPTIONS_TO_RETRY) and not request.meta.get('dont_retry', False):
            return self._retry(request, exception, spider)

    def _retry(self, request, reason, spider):
        retries = request.meta.get('retry_times', 0) + 1

        if retries <= self.max_retry_times:
            logger.debug("Retrying %(request)s (failed %(retries)d times): %(reason)s",
                         {'request': request, 'retries': retries, 'reason': reason},
                         extra = {'spider': spider})
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retries
            retryreq.dont_filter = True
            retryreq.priority = request.priority + self.priority_adjust

            request.meta['req_count'] = request.meta.get('req_count', 0) + 1

            if retries == self.max_retry_times:
                if request.meta.get('is_proxy', False):
                    proxymng.delete_proxy(retryreq.meta.get('proxy'))
                    retryreq.meta['proxy'] = proxymng.get_proxy()

            return retryreq
        else:
            logger.debug("Gave up retrying %(request)s (failed %(retries)d times): %(reason)s",
                         {'request': request, 'retries': retries, 'reason': reason},
                         extra = {'spider': spider})
