#!/usr/bin/env python3
# encoding=utf8
"""
贴吧爬虫主程序，通过 launcher.py 调用。依靠参数决定处理过程的细节。

使用方法
python launcher.py --ID 4842388571 --TieziKind 0 --Date 2016-11-12\
--Time 00:00 --SortedTop 0 --OnlySender 0 --OnlyPicsUser 0 --DownloadPics 0
"""

import os
import re
import logging
import datetime
import argparse
import urllib.request as request

# 可以更改的变量(早期测试使用，现已使用命令行参数传递)
TIEZIKIND = 0  # 达音科吧有点不同，设为1才能截取；正常情况设为0
TIEZIID = 4842388571  # 帖子 ID 号
DEADLINE = '2016-11-12 00:00'
FLAG_SORTEDTOP = 0  # 打印发图总数排行前 N 个用户，0 不打印 !!!不可大于总参与用户数量，如果报错，请改小
FLAG_ONLYSENDER = 0  # 1 只看楼主；0 所有楼层
FLAG_DOWNLOADPICS = 0  # 1 下载图片；0 不下载图片

# 以下全局变量仅供自己使用
FLAG_GETREGEXRESULT = False
NEWPATH = ""
TIEZI = None

# Debug 输出
logging.basicConfig(format='%(message)s', level=logging.INFO)


def set_argparse():
    """从命令行获取工作参数
    参数的工作模式如下
    python launcher.py --ID 4842388571 --TieziKind 0 --Date 2016-11-12\
    --Time 00:00 --SortedTop 0 --OnlySender 0 --OnlyPicsUser 0 --DownloadPics 0
    """
    global TIEZIKIND
    global TIEZIID
    global DEADLINE
    global FLAG_SORTEDTOP
    global FLAG_ONLYSENDER
    global FLAG_DOWNLOADPICS
    parser = argparse.ArgumentParser()
    parser.add_argument("--ID", help="帖子ID号，网页地址内有")
    parser.add_argument("--TieziKind", help="达音科吧用1，其它用0", type=int)
    parser.add_argument("--Date", help="只抓取该时间以前的帖子")
    parser.add_argument("--Time", help="只抓取该时间以前的帖子")
    parser.add_argument("--SortedTop", help="0不排序，或者对前N名进行排序", type=int)
    parser.add_argument("--OnlySender", help="1 只看楼主；2 全部帖子", type=int)
    parser.add_argument("--DownloadPics", help="1 下载图片；0 不下载图片", type=int)
    args = parser.parse_args()
    TIEZIKIND = args.TieziKind
    TIEZIID = args.ID
    DEADLINE = args.Date + ' ' + args.Time
    FLAG_SORTEDTOP = args.SortedTop
    FLAG_ONLYSENDER = args.OnlySender
    FLAG_DOWNLOADPICS = args.DownloadPics
    logging.debug(args)
    return


class PostTiezi(object):
    """当前被爬的帖子的统计信息初始化"""

    def __init__(self):
        self.id_list = []
        self.content_list = []
        self.post_sum = 0
        self.page_sum = 0
        self.title = ''
        self.pic_sum = 0

    def add(self, con):
        """
        保存信息： set0 ID 1 性别 2 等级 3 楼层 4 帖子内容 5 图片内容 6 楼层数 7 图片数量
        获取信息: 性别，等级，发帖时间，楼层，ID，发帖内容
        """
        if con[4] not in self.id_list:
            self.id_list.append(con[4])
            tmp = list()
            tmp.append(con[4])  # 0 ID
            if con[0] == u'1':
                tmp.append('男')  # 1 性别
            elif con[0] == u'2':
                tmp.append('女')  # 1 性别
            else:
                tmp.append('无')
            tmp.append(int(con[1]))  # 2 等级
            tmp.append(str(con[3]) + '楼 ' + str(con[2]) + '\n')  # 3 楼层
            tmp.append('- 第 ' + str(con[3]) + ' 楼:\n```\n' + con[5] +
                       '\n```\n')  # 4 帖子内容
            tmp[4] = tmp[4].replace('> \n', '')
            tmp[4] = tmp[4].rstrip(' >\n')
            if len(con[6]) != 0:
                tmp.append(con[6])  # 5 图片内容
            else:
                tmp.append([])
            tmp.append(tmp[3].count('\n'))  # 6 楼层数
            tmp.append(len(con[6]))  # 7 图片数量
            self.pic_sum += len(con[6])
            self.content_list.append(tmp)
        else:
            self.update(con)

    def update(self, con):
        """更新已存在 ID 的内容"""
        index = self.id_list.index(con[4])
        # 合并楼层索引
        self.content_list[index][3] += str(con[3]) + '楼 ' + str(con[2]) + '\n'
        # 合并文本回复
        self.content_list[index][4] += '\n- 第 ' + str(
            con[3]) + ' 楼:\n```\n' + con[5] + '\n```\n'
        self.content_list[index][4] = self.content_list[index][4].replace(
            '> \n', '')
        self.content_list[index][4] = self.content_list[index][4].rstrip(
            '\n> ')
        # 插入图片信息
        if len(con[6]) != 0:
            for item in con[6]:
                self.content_list[index][5].append(item)
        # 更新统计信息
        self.content_list[index][6] += 1  # 6 楼层数
        self.content_list[index][7] += len(con[6])  # 7 图片数
        self.pic_sum += len(con[6])


class BDTB(object):
    """获取帖子的源代码并进行分析"""

    def __init__(self):
        #       'http://tieba.baidu.com/p/3138733512?see_lz=1&pn=1'  百度贴吧URL地址
        self.base_url = 'http://tieba.baidu.com/p/'
        self.see_only_lz = '?see_lz='  # =1只看楼主 =0查看全部
        self.url_pn = '&pn='  # 代表页码

    def recode_page_content(self, pagecontent, page):
        """利用正则表达式获取需要的信息"""
        global TIEZIKIND
        if TIEZIKIND == 0:
            # 获取信息:性别，等级，发帖时间，楼层，ID，发帖内容
            pattern = re.compile(
                r'<div class="l_post j_l_post l_post_bright.*?user_name&quot;:&quot;.*?&quot.*?user_sex&quot;:(.*?),.*?level_id&quot;:(.*?),.*?date&quot;:&quot;(.*?)&quot.*?post_no&quot;:(.*?),.*?<li class="icon">.*?<div class="icon_relative j_user_card".*?<img username="(.*?)".*?clearfix">            (.*?)</div>',
                re.DOTALL | re.IGNORECASE | re.MULTILINE)
        elif TIEZIKIND == 1:
            # 获取信息:楼层，ID，等级，发帖内容，发帖时间
            pattern = re.compile(
                r'post_no.*?:(.*?),.*?<img username="(.*?)".*?<div class="d_badge_lv">(.*?)</div>.*?class=".*?j_d_post_content.*?">            (.*?)</div>.*?(\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2})',
                re.DOTALL | re.IGNORECASE | re.MULTILINE)

        source = pagecontent
        #        print source
        #        print type(source)
        results = re.findall(pattern, source)

        global FLAG_GETREGEXRESULT

        if (FLAG_GETREGEXRESULT):
            global NEWPATH
            #            print NewPath
            file_save = open(
                NEWPATH + '/[RegexResults%s].txt' % page,
                'w',
                encoding='utf-8')
            for item in results:
                file_save.write('%s\n' % str(item))
            file_save.close()

        return results

    def decode_tieze_title(self, pagecontent):
        """获取帖子标题"""
        pattern = re.compile(r'<h\d.*?class="core_title_txt.*?title="(.*?)"',
                             re.S)
        title = re.search(pattern, pagecontent)
        return title.group(1)

    def decode_page_content_num(self, pagecontent):
        """获取页面回复数量和总页码"""
        patten = re.compile(
            '<li class="l_reply_num".*?<span class="red".*?>(.*?)' +
            '</span>.*?<span class="red".*?>(.*?)</span>', re.S)
        num = re.search(patten, pagecontent)
        return num

    def get_page_content(self, url):
        """获取页面html文本内容"""
        request_res = request.urlopen(url)
        # decode 可以选则 'iso-8859-1' 'utf-8' 有些编码可能是混合式 容易出错
        response = request_res.read().decode('utf-8', errors='ignore')
        return response

    def start(self):
        """开始工作"""
        global TIEZIID
        global FLAG_ONLYSENDER
        urlid = TIEZIID
        see_lz = FLAG_ONLYSENDER
        sss = self.base_url + str(urlid) + self.see_only_lz + str(
            see_lz) + self.url_pn + str(1)
        #         sss = 'http://tieba.baidu.com/p/3138733512?see_lz=0&pn=1'
        pagecontent = self.get_page_content(sss)

        num = self.decode_page_content_num(pagecontent)
        # 保存页码数量
        self.page_num = num.group(2)
        self.title = self.decode_tieze_title(pagecontent)

        # 删除 title 中不能做文件名的字符
        title_name = self.title.encode('UTF-8')
        title_name = title_name.translate(None, b'*|/\\<>:"?')
        title_name = title_name.decode('UTF-8')
        logging.info('开始抓取:%s', title_name)
        logging.info('%s回复贴，共%s页', num.group(1), num.group(2))

        global NEWPATH
        global FLAG_DOWNLOADPICS
        global Flag_OnlyPicsUser
        global TIEZI
        global TIEZIKIND
        global DEADLINE

        if DEADLINE != '':
            deadtime = datetime.datetime.strptime(DEADLINE, '%Y-%m-%d %H:%M')

        NEWPATH = './' + str(title_name)

        if not os.path.exists(NEWPATH):
            os.makedirs(NEWPATH)

        TIEZI.post_sum = num.group(1)
        TIEZI.page_sum = num.group(2)
        TIEZI.title = title_name

        delete_br = re.compile(r'<br>', re.DOTALL | re.IGNORECASE |
                               re.MULTILINE)
        delete_img = re.compile(r'<img.*?>(<br>){0,}', re.DOTALL |
                                re.IGNORECASE | re.MULTILINE)
        picpattern = re.compile('<img.*?class="BDE_Image".*?src="(.*?)".*?>',
                                re.DOTALL | re.IGNORECASE | re.MULTILINE)
        delatpattern = re.compile('<.*?>', re.DOTALL | re.IGNORECASE |
                                  re.MULTILINE)
        # range函数不包括最大的值
        for i in range(1, int(self.page_num) + 1):
            pagecontent = self.get_page_content(self.base_url + str(
                urlid) + self.see_only_lz + str(see_lz) + self.url_pn + str(i))
            logging.info(self.base_url + str(urlid) + self.see_only_lz + str(
                see_lz) + self.url_pn + str(i))
            content = self.recode_page_content(pagecontent, i)
            """
            ----------------------------------------\n\n
            楼层：\t\5\n
            ＩＤ：\t\6\n
            等级：\t\3\n
            性别：\t\2\n
            发帖时间：\4\n\n
            内容：\n\7\n
            """
            for con in content:
                if TIEZIKIND == 0:
                    # 获取信息:性别，等级，发帖时间，楼层，ID，发帖内容
                    tmp_list = list(con)
                elif TIEZIKIND == 1:
                    # 获取信息:楼层，ID，等级，发帖内容，发帖时间
                    tmp_list = []
                    tmp_list.append(r'0')
                    tmp_list.append(con[2])
                    tmp_list.append(con[4])
                    tmp_list.append(con[0])
                    tmp_list.append(con[1])
                    tmp_list.append(con[3])

                # 检查设置的统计截止期
                if DEADLINE != '':
                    post_time = datetime.datetime.strptime(tmp_list[2],
                                                           '%Y-%m-%d %H:%M')
                    if (deadtime - post_time).total_seconds() < 0:
                        return

                pics = re.findall(picpattern, tmp_list[5])
                text = re.sub(delete_img, r'', tmp_list[5])
                text = re.sub(delete_br, r'\n', text)
                text = re.sub(delatpattern, r'', text)
                if text == '':
                    tmp_list[5] = '无内容'
                else:
                    tmp_list[5] = text
                tmp_list.append(pics)
                TIEZI.add(tmp_list)
                cnt = int(1)
                if FLAG_DOWNLOADPICS == 1:  # 下载图片
                    for pic_item in pics:
                        pic_item.split('.')[-1]
                        request.urlretrieve(
                            pic_item, NEWPATH + '/Pic[%s][%s楼-%d]_%s.%s' %
                            (tmp_list[4], tmp_list[3], cnt, tmp_list[0],
                             pic_item.split('.')[-1]))
                        cnt += 1


def save_file(list_print):
    """保存最终结果"""
    global TIEZIID  # 打印用
    global NEWPATH
    global FLAG_ONLYSENDER
    global TIEZI
    global DEADLINE
    flag_only_picsuser = 0
    file_save_withpics = ['无图', '有图']
    file_sort_method_name = ['图数_回复时间', '图数_等级', '等级_图数', '回复数_等级']
    for flag_only_picsuser in range(0, len(file_save_withpics)):
        # 统计发图的用户数量
        static_join_sum = 0
        # 用户输出编号，自用
        cnt = int(1)
        # 遍历所有帖子的汇总信息
        if FLAG_ONLYSENDER == 1:
            file_save = open(
                NEWPATH + '/[帖子内容-楼主%s].txt' %
                file_save_withpics[flag_only_picsuser],
                'w',
                encoding='utf-8')
        else:
            file_save = open(
                NEWPATH + '/[帖子内容-全部%s].txt' %
                file_save_withpics[flag_only_picsuser],
                'w',
                encoding='utf-8')

        file_save.write('# 原帖地址\nhttp://tieba.baidu.com/p/%s\n\n# %s\n\n' %
                        (TIEZIID, TIEZI.title))
        file_save.write('%s回复贴，共%s页\n统计结果于本文末尾\n' %
                        (TIEZI.post_sum, TIEZI.page_sum))
        if flag_only_picsuser == 1:
            file_save.write('PS：**本文只打印有照片的楼层**\n\n')
        else:
            file_save.write('PS：**本文打印所有楼层**\n\n')
        for tmp in list_print:
            if flag_only_picsuser == 1 and tmp[7] == 0:
                continue
            file_save.write('----------------------------------------\n\n\
                ## ＩＤ：\t%s\n顺序编号：%d\n' % (tmp[0], cnt))
            cnt += 1
            file_save.write('性别：\t%s\n' % tmp[1])
            file_save.write('等级：\t%s\n' % tmp[2])
            file_save.write('\n### 楼层  贡献%d层\n' % tmp[6])
            file_save.write('%s\n' % tmp[3])
            file_save.write('### 文字内容\n%s\n\n' % tmp[4])
            if tmp[7] != 0:
                static_join_sum += 1
                file_save.write('### 图片内容 %d 张\n' % tmp[7])
                for cnt_tmp in tmp[5]:
                    file_save.write('![](%s)\n' % cnt_tmp)
            file_save.write('\n')
        file_save.write('# 原帖地址\nhttp://tieba.baidu.com/p/%s\n\n# %s\n\n' %
                        (TIEZIID, TIEZI.title))
        file_save.write('%s回复贴，共%s页\n\n' % (TIEZI.post_sum, TIEZI.page_sum))
        # 写入统计信息
        file_save.write('========================================\n# 统计结果\n\n')
        file_save.write('### 发帖参与人数：%d\n' % len(list_print))
        file_save.write('### 爆照参与人数：%d（楼主若发图，也算在里面。根据实际情况减除。）\n' %
                        static_join_sum)
        file_save.write('### 收获照片总数：%d\n' % TIEZI.pic_sum)
        if DEADLINE == '':
            file_save.write('### 统计截止日期：%s\n' %
                            datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
        else:
            file_save.write('### 统计截止日期：%s\n' % DEADLINE)
        file_save.write('========================================\n# 统计结果\n\n')
        file_save.write(
            '|  序号  |              ID              | 贴吧等级 |        Info        |\n'
        )
        file_save.write(
            '| :---: |             :--:             |  :---:  |        :---        |\n'
        )
        for cnt in range(0, len(list_print)):
            file_save.write('|  %4d  | %-30s |   %3d   |[%3d图 %3d层 %s]|\n' % (
                cnt + 1, str(list_print[cnt][0]), list_print[cnt][2],
                list_print[cnt][7], list_print[cnt][6], list_print[cnt][1]))
        file_save.write('\n')
        file_save.close()
        flag_only_picsuser += 1
    # 全局结果保存完毕
    # 保存所有排序结果
    file_sort_method_index = 0
    for file_sort_method_index in range(0, len(file_sort_method_name)):
        file_save = open(
            NEWPATH + '/[统计结果-%s].txt' %
            file_sort_method_name[file_sort_method_index],
            'w',
            encoding='utf-8')
        if file_sort_method_index == 0:
            list_print.sort(key=lambda x: x[7], reverse=True)
            file_save.write('排名先遵循发图总数，再依据第一次回复时间\n\n')
        # 1. 发图数量 -> 贴吧等级
        elif file_sort_method_index == 1:
            list_print.sort(key=lambda x: (x[7], x[2]), reverse=True)
            file_save.write('排名先遵循发图总数，再依据贴吧等级\n\n')
        # 3. 贴吧等级 -> 发图数量
        elif file_sort_method_index == 2:
            list_print.sort(key=lambda x: (x[2], x[7]), reverse=True)
            file_save.write('排名先遵循贴吧等级，再依据发图数量\n\n')
        elif file_sort_method_index == 3:
            list_print.sort(key=lambda x: (x[6], x[2]), reverse=True)
            file_save.write('排名先遵循回复数量，再依据贴吧等级\n\n')
        file_save.write('========================================\n# 排序结果\n\n')
        file_save.write('### 发帖参与人数：%d\n' % len(list_print))
        file_save.write('### 爆照参与人数：%d（楼主若发图，也算在里面。根据实际情况减除。）\n' %
                        static_join_sum)
        file_save.write('### 收获照片总数：%d\n' % TIEZI.pic_sum)
        if DEADLINE == '':
            file_save.write('### 统计截止日期：%s\n' %
                            datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
        else:
            file_save.write('### 统计截止日期：%s\n' % DEADLINE)
        file_save.write('========================================\n# 统计结果\n\n')
        file_save.write(
            '|  序号  |              ID              | 贴吧等级 |        Info        |\n'
        )
        file_save.write(
            '| :---: |             :--:             |  :---:  |        :---        |\n'
        )
        for cnt in range(0, len(list_print)):
            file_save.write('|  %4d  | %-30s |   %3d   |[%3d图 %3d层 %s]|\n' % (
                cnt + 1, str(list_print[cnt][0]), list_print[cnt][2],
                list_print[cnt][7], list_print[cnt][6], list_print[cnt][1]))
        file_save.write('\n')
        file_save.close()


def save_sort(sorted_top):
    """对前位进行排序"""
    global TIEZI
    list_print = TIEZI.content_list
    sort_method = ['发图总数-第一次回复时间', '发图总数-贴吧等级', '贴吧等级-发图数量', '回复数量-贴吧等级']
    # 如果用户数不够，修改SortedTopN
    if sorted_top > len(TIEZI.content_list):
        sorted_top = len(TIEZI.content_list)
    # 写入文件
    file_save = open(
        NEWPATH + '/[Top %d].txt' % sorted_top, 'w', encoding='utf-8')
    if DEADLINE == '':
        file_save.write('# 统计截止日期：%s\n' %
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    else:
        file_save.write('# 统计截止日期：%s\n' % DEADLINE)
    # 写入 TOC
    file_save.write(
        '\n# 索引\n\n  * [发图总数，第一次回复时间](#%s)\  * [发图总数，贴吧等级](#%s)\n  * [贴吧等级，发图数量](#%s)\n  * [回复数量，贴吧等级](#%s)\n\n========================================\n'
        % (sort_method[0], sort_method[1], sort_method[2], sort_method[3]))
    # 排序处理
    sort_method_index = 0
    for sort_method_index in range(0, len(sort_method)):
        # 0 ID 1 性别 2 等级 3 楼层 4 帖子内容 5 图片内容 6 楼层数 7 图片数量
        # 0. 发图数量 -> 首次回贴时间
        if sort_method_index == 0:
            list_print.sort(key=lambda x: x[7], reverse=True)
        # 1. 发图数量 -> 贴吧等级
        elif sort_method_index == 1:
            list_print.sort(key=lambda x: (x[7], x[2]), reverse=True)
        # 2. 贴吧等级 -> 发图数量
        elif sort_method_index == 2:
            list_print.sort(key=lambda x: (x[2], x[7]), reverse=True)
        elif sort_method_index == 3:
            list_print.sort(key=lambda x: (x[6], x[2]), reverse=True)
        file_save.write('\n# [%s](#索引)\n\n' % sort_method[sort_method_index])
        # 输出所有用户的表格
        for cnt in range(0, sorted_top):
            file_save.write(
                '----------------------------------------[返回排序标题](#%s)\n### Top：%d\nＩＤ：\t%s\n'
                %
                (sort_method[sort_method_index], cnt + 1, list_print[cnt][0]))
            file_save.write('性别：\t%s\n' % list_print[cnt][1])
            file_save.write('等级：\t%s\n' % list_print[cnt][2])
            file_save.write('\n#### 楼层  贡献%d层\n' % list_print[cnt][6])
            file_save.write('%s\n' % list_print[cnt][3])
            file_save.write('#### 文字内容\n%s\n\n' % list_print[cnt][4])
            if list_print[cnt][7] != 0:
                file_save.write('#### 图片内容 %d 张\n' % list_print[cnt][7])
                for list_item in list_print[cnt][5]:
                    file_save.write('![](%s)\n' % list_item)
            file_save.write('\n')
        sort_method_index += 1
        file_save.write('\n')
    file_save.close()


def main():
    """主函数"""
    global TIEZI
    global FLAG_SORTEDTOP
    set_argparse()
    TIEZI = PostTiezi()
    bdtb = BDTB()
    bdtb.start()
    save_file(TIEZI.content_list)
    if FLAG_SORTEDTOP > 0:
        save_sort(FLAG_SORTEDTOP)
    logging.info('\n--%s 完成--' % TIEZI.title)
    exit()


if __name__ == '__main__':
    main()
