#!/usr/bin/python
#_*_encoding=utf8_*_
#Python 3.5.2

import sys, getopt
import logging
import subprocess
import time

# Debug 输出
logging.basicConfig(format = '%(message)s',level = logging.INFO)

"""
在此处添加任务
意义为
'4842388571', '0', '2016-11-12', '00:00', '20', '0', '0'
1: 帖子ID：在地址栏可以找到
2: 帖子种类：0 大部分帖子 1 达音科吧帖子
3: 该时间以后的帖子不统计
4: 该时间以后的帖子不统计
5: Top N 排名前N位。0 表示不排序
6: 1 只看楼主；2 全部帖子
7: 1 下载图片；0 不下载图片
"""

TieziList = [
            ['4842388571', '0', '2016-11-12', '00:00', '20', '0', '0'], # 国砖吧cayin爆照贴
            # ['4836451867', '1', '2016-11-12', '00:00', '20', '0', '0'], # 达音科双11第二轮活动贴
]

pythonInSystem = ''

def checkPlatform():
    global pythonInSystem
    import platform
    sys = platform.system()
    if sys == 'Darwin':
        pythonInSystem = 'python3'
        sys = 'MacOS'
    if sys == 'Linux':
        pythonInSystem = 'python3'
    elif sys == 'Windows':
        pythonInSystem = 'python'
    logging.info('System is: %s.\nPython command use: %s\n' % (sys,pythonInSystem))

def main():
    processPoll = []
    global pythonInSystem
    checkPlatform()
    for item in TieziList:
        processPoll.append(subprocess.Popen('%s TiebaCrawler.py --ID %s --TieziKind %s --Date %s --Time %s --SortedTop %s --OnlySender %s --DownloadPics %s' % (pythonInSystem, item[0],item[1],item[2],item[3],item[4],item[5],item[6]), shell = True))
    while len(processPoll) != 0:
        logging.debug('工作进程数量:%d' % len(processPoll))
        for item in processPoll:
            if item.poll() is not None:
                processPoll.remove(item)
        time.sleep(0.5)
    logging.info('==========\n!!!所有统计任务完成!!!\n')
    exit(0)

if __name__ == '__main__':
    main()