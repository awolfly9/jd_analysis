#-*- coding: utf-8 -*-

import re
import subprocess
import time


# 服务器使用，清理端口占用
import sys


def kill_ports(ports):
    for port in ports:
        print('kill %s start' % port)
        popen = subprocess.Popen('lsof -i:%s' % port, shell = True, stdout = subprocess.PIPE)
        (data, err) = popen.communicate()
        print('data:\n%s  \nerr:\n%s' % (data, err))

        pattern = re.compile(r'\b\d+\b', re.S)
        pids = re.findall(pattern, data)

        print('pids:%s' % str(pids))

        for pid in pids:
            if pid != '' and pid != None:
                try:
                    print('pid:%s' % pid)
                    popen = subprocess.Popen('kill -9 %s' % pid, shell = True, stdout = subprocess.PIPE)
                    (data, err) = popen.communicate()
                    print('data:\n%s  \nerr:\n%s' % (data, err))
                except Exception, e:
                    print('kill_ports exception:%s' % e)

        print('kill %s finish' % port)

    time.sleep(1)


if __name__ == '__main__':
    ports = sys.argv
    kill_ports(ports = ports)
