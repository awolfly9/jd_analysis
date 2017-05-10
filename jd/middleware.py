#-*- coding: utf-8 -*-

import datetime
import utils

from django.utils.deprecation import MiddlewareMixin
from jd.models import JDVisit


class JDVisitMiddleware(MiddlewareMixin):
    def process_request(self, request):
        page = request.path
        if 'runspider' in page and request.method == 'POST':
            ip = utils.get_visiter_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            vt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            jd_url = request.POST.get('url')
            visit = JDVisit(id = None, ip = ip, ip_address = '', visit_time = vt, user_agent = user_agent,
                            jd_url = jd_url, ip_hight_success = '', ip_hight_address = '')

            visit.save()
        elif 'randitem' in page and request.method == 'POST':
            ip = utils.get_visiter_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            vt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            jd_url = 'randitem'
            visit = JDVisit(id = None, ip = ip, ip_address = '', visit_time = vt, user_agent = user_agent,
                            jd_url = jd_url, ip_hight_success = '', ip_hight_address = '')

            visit.save()
