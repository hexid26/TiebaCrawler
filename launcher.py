#!/usr/bin/env python3
# encoding=utf8
"""贴吧爬虫的启动脚本，用来批量启动爬虫"""

import logging
import subprocess
import time

# Debug 输出

logging.basicConfig(format='%(message)s', level=logging.INFO)
"""
在此处添加任务
意义为
'4842388571', '0', '2016-11-12', '00:00', '20', '0', '0'
1: 帖子ID：在地址栏可以找到
2: 帖子种类：0 大部分帖子 1 达音科吧帖子
3: 该时间以后的帖子不统计
4: 该时间以后的帖子不统计
5: Top N 排名前N位。0 表示不排序
6: 1 只看楼主；0 全部帖子
7: 1 下载图片；0 不下载图片
"""

TIEZI_LIST = [
    # 国砖吧cayin爆照贴
    # ['4842388571', '0', '2016-11-12', '00:00', '10', '0', '0'],
    # 耳机吧HiFiMan抽奖贴
    # ['4849853857', '0', '2016-11-12', '00:00', '0', '0', '0'],
    # 达音科双11第二轮活动贴
    # ['4867759631', '0', '2016-11-25', '00:00', '0', '0', '0'],
    ['5090126775', '0', '2017-05-03', '00:00', '3', '0', '0']
]

PYTHON_IN_SYSTEM = ''


def check_platform():
    """检查当前运行平台（环境）"""
    global PYTHON_IN_SYSTEM
    import platform
    sys = platform.system()
    if sys == 'Darwin':
        PYTHON_IN_SYSTEM = 'python'
        sys = 'MacOS'
    if sys == 'Linux':
        PYTHON_IN_SYSTEM = 'python'
    elif sys == 'Windows':
        PYTHON_IN_SYSTEM = 'python'
    logging.info('System is: %s.\nPython command use: %s\n', sys,
                 PYTHON_IN_SYSTEM)


def main():
    """主函数"""
    process_poll = []
    global PYTHON_IN_SYSTEM
    check_platform()
    for item in TIEZI_LIST:
        process_poll.append(
            subprocess.Popen(
                '%s TiebaCrawler.py --ID %s --TieziKind %s --Date %s --Time \
                %s --SortedTop %s --OnlySender %s --DownloadPics %s' %
                (PYTHON_IN_SYSTEM, item[0], item[1], item[2], item[3], item[4],
                 item[5], item[6]),
                shell=True))
    while len(process_poll) != 0:
        logging.debug('工作进程数量:%d', len(process_poll))
        for item in process_poll:
            if item.poll() is not None:
                process_poll.remove(item)
        time.sleep(0.5)
    logging.info('==========\n!!!所有统计任务完成!!!\n')
    exit(0)


if __name__ == '__main__':
    main()
