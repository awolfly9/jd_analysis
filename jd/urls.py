#-*- coding: utf-8 -*-

import views

from django.conf.urls import url

urlpatterns = [
    url(r'^runspider$', views.runspider, name = 'runspider'),
    url(r'^randitem', views.randitem, name = 'randitem'),
    url(r'^analysis$', views.analysis, name = 'analysis'),
    url(r'^register_spider$', views.register_spider, name = 'register_spider'),
    url(r'^delete_spider$', views.delete_spider, name = 'delete_spider'),
    url(r'^full$', views.FullView.as_view(), name = 'full'),
    url(r'^full_comment', views.full_comment, name = 'full_comment'),
    url(r'^full_result/(?P<param>.*)', views.AnalysisResultView.as_view(), name = 'result'),
    url(r'^$', views.IndexView.as_view(), name = 'index'),
]
