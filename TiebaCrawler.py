#!/usr/bin/python
#_*_encoding=utf8_*_
#Python 3.5.2

# 使用方法
# python launcher.py --ID 4842388571 --TieziKind 0 --Date 2016-11-12 --Time 00:00 --SortedTop 0 --SortedMethod 0 --OnlySender 0 --OnlyPicsUser 0 --DownloadPics 0
import sys, getopt
import urllib.request
import os
import re
import logging
import datetime
import argparse

# 可以更改的变量(早期测试使用，现已使用命令行参数传递)
TieziKind = 0             # 达音科吧有点不同，设为1才能截取；正常情况设为0
TieziID = 4842388571      # 帖子 ID 号
Deadline = '2016-11-12 00:00'
Flag_SortedTop = 0       # 打印发图总数排行前 N 个用户，0 不打印 !!!不可大于总参与用户数量，如果报错，请改小
Flag_SortedMethod = 0     # 按照下方说明修改
# 0. 发图数量 -> 首次回贴时间
# 1. 发图数量 -> 贴吧等级
# 2. 贴吧等级 -> 发图数量
Flag_OnlySender = 0       # 1 只看楼主；0 所有楼层
Flag_OnlyPicsUser = 0     # 1 只保存有图片的楼层；0 保存所有回复楼层
Flag_DownloadPics = 0     # 1 下载图片；0 不下载图片


# 以下全局变量仅供自己使用
Flag_GetRegexResult = False
NewPath = ""
tiezi = None

# Debug 输出
logging.basicConfig(format = '%(message)s',level = logging.INFO)

def setArgparse():
    global TieziKind
    global TieziID
    global Deadline
    global Flag_SortedTop
    global Flag_SortedMethod
    global Flag_OnlySender
    global Flag_OnlyPicsUser
    global Flag_DownloadPics
    parser = argparse.ArgumentParser()
    parser.add_argument("--ID", help="帖子ID号，网页地址内有")
    parser.add_argument("--TieziKind", help="达音科吧用1，其它用0", type = int)
    parser.add_argument("--Date", help="只抓取该时间以前的帖子")
    parser.add_argument("--Time", help="只抓取该时间以前的帖子")
    parser.add_argument("--SortedTop", help="0不排序，或者对前N名进行排序", type = int)
    parser.add_argument("--SortedMethod", help="0 发图数量 -> 首次回贴时间\n1 发图数量 -> 贴吧等级\n2 贴吧等级 -> 发图数量", type = int)
    parser.add_argument("--OnlySender", help="1 只看楼主；2 全部帖子", type = int)
    parser.add_argument("--OnlyPicsUser", help="1 只保存有图片的楼层；0 保存所有回复楼层", type = int)
    parser.add_argument("--DownloadPics", help="1 下载图片；0 不下载图片", type = int)
    args = parser.parse_args()
    TieziKind = args.TieziKind
    TieziID = args.ID
    Deadline = args.Date + ' ' + args.Time
    Flag_SortedTop = args.SortedTop
    Flag_SortedMethod = args.SortedMethod
    Flag_OnlySender = args.OnlySender
    Flag_OnlyPicsUser = args.OnlyPicsUser
    Flag_DownloadPics = args.DownloadPics
    logging.debug(TieziKind)
    logging.debug(TieziID)
    logging.debug(Deadline)
    logging.debug(Flag_SortedTop)
    logging.debug(Flag_SortedMethod)
    logging.debug(Flag_OnlySender)
    logging.debug(Flag_OnlyPicsUser)
    logging.debug(Flag_DownloadPics)
    # pdb.set_trace()
    logging.debug(args)
    return

class PostTiezi:
    def __init__(self):
        self.idList = []
        self.contentList = []
        self.postSum = 0
        self.pageSum = 0
        self.title = ''

    def add(self,con):
        # 保存信息：0 ID 1 性别 2 等级 3 楼层 4 帖子内容 5 图片内容 6 楼层数 7 图片数量

        # 获取信息: 性别，等级，发帖时间，楼层，ID，发帖内容
#        logging.debug('%s' % con)
        if con[4] not in self.idList:
            self.idList.append(con[4])
#            logging.debug('%s' % self.idList)
            tmp = list()
            tmp.append(con[4])     # 0 ID
            if con[0] == u'1':
                tmp.append('男')   # 1 性别
            elif con[0] == u'2':
                tmp.append('女')   # 1 性别
            else:
                tmp.append('无')
            tmp.append(int(con[1]))     # 2 等级
            tmp.append(str(con[3])+'楼 '+str(con[2])+'\n')     # 3 楼层
            tmp.append('- 第 '+str(con[3])+' 楼:\n```\n'+con[5]+'\n```\n')     # 4 帖子内容
            tmp[4] = tmp[4].replace('> \n', '')
            tmp[4] = tmp[4].rstrip(' >\n')
#            logging.debug('-----\ncon[6] has %d items\n%s\n' % (len(con[6]), con[6]))
            if len(con[6]) != 0:
                tmp.append(con[6])       # 5 图片内容
            else:
                tmp.append([])
#            logging.debug('%s'%tmp)
            tmp.append(tmp[3].count('\n')) # 6 楼层数
            tmp.append(len(con[6]))      # 7 图片数量
            self.contentList.append(tmp)
        else:
            self.update(con)

    def update(self,con):
        #更新已存在 ID 的内容
        index = self.idList.index(con[4])
#        logging.debug(con)
        # 合并楼层索引
        self.contentList[index][3]+= str(con[3])+'楼 '+str(con[2])+'\n'
        # 合并文本回复
        self.contentList[index][4]+= '\n- 第 ' + str(con[3]) + ' 楼:\n```\n' + con[5]+'\n```\n'
        self.contentList[index][4] = self.contentList[index][4].replace('> \n', '')
        self.contentList[index][4] = self.contentList[index][4].rstrip('\n> ')
        # 插入图片信息
#        logging.debug('-----\ncon[6] has %d items\n%s\n' % (len(con[6]), con[6]))
        if len(con[6]) != 0:
#            logging.debug('-----\nItem at the index is:\n%s\n' % self.contentList[index])
            for item in con[6]:
                self.contentList[index][5].append(item)
#        logging.debug('%s' % self.contentList[index])
        # 更新统计信息
        self.contentList[index][6] += 1             # 6 楼层数
        self.contentList[index][7] += len(con[6])   # 7 图片数




class BDTB:
    def __init__(self):
#       'http://tieba.baidu.com/p/3138733512?see_lz=1&pn=1'  百度贴吧URL地址
        self.baseUrl = 'http://tieba.baidu.com/p/'
        self.seellz = '?see_lz=' #=1只看楼主 =0查看全部
        self.urlpn = '&pn=' #代表页码

    #获取信息
    def decodePageContent(self,pagecontent,page):
        global TieziKind
        if TieziKind == 0:
            #获取信息:性别，等级，发帖时间，楼层，ID，发帖内容
            pattern = re.compile(r'<div class="l_post j_l_post l_post_bright.*?user_name&quot;:&quot;.*?&quot.*?user_sex&quot;:(.*?),.*?level_id&quot;:(.*?),.*?date&quot;:&quot;(.*?)&quot.*?post_no&quot;:(.*?),.*?<li class="icon">.*?<div class="icon_relative j_user_card".*?<img username="(.*?)".*?clearfix">            (.*?)</div>', re.DOTALL | re.IGNORECASE | re.MULTILINE)
        elif TieziKind == 1:
            #获取信息:楼层，ID，等级，发帖内容，发帖时间
            pattern = re.compile(r'post_no.*?:(.*?),.*?<img username="(.*?)".*?<div class="d_badge_lv">(.*?)</div>.*?class=".*?j_d_post_content.*?">            (.*?)</div>.*?(\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2})', re.DOTALL | re.IGNORECASE | re.MULTILINE)

        source = pagecontent
#        print source
#        print type(source)
        results = re.findall(pattern, source);

        global Flag_GetRegexResult

        if (Flag_GetRegexResult):
            global NewPath
#            print NewPath
            f = open(NewPath + '/[RegexResults%s].txt' % page,'w',encoding='utf-8')
            for item in results:
                f.write('%s\n' % str(item))
            f.close()

        return results
    #获取帖子标题
    def decodeTieziTitle(self,pagecontent):
        # pattern = re.compile(r'<h\d.*?class="core_title_txt.*?>(.*?)</h\d>',re.S)
        pattern = re.compile(r'<h\d.*?class="core_title_txt.*?title="(.*?)"',re.S)
        # <h\d.*?class="core_title_txt.*?title="(.*?)"
        title = re.search(pattern, pagecontent)
        logging.debug(title.group(1))
        return title.group(1)
    #获取页面回复数量和总页码
    def decodePageContentNum(self,pagecontent):
        patten = re.compile('<li class="l_reply_num".*?<span class="red".*?>(.*?)'+
                            '</span>.*?<span class="red".*?>(.*?)</span>',re.S)
        num =re.search(patten, pagecontent);
        return num
    #获取页面html文本内容
    def getPageContent(self,url):
        request = urllib.request.urlopen(url)
        # decode 可以选则 'iso-8859-1' 'utf-8'
        response = request.read().decode('utf-8',errors = 'ignore')  #有些编码可能是混合式 容易出错
        return response
    def start(self):
        global TieziID
        global Flag_OnlySender
        urlid = TieziID
        see_lz = Flag_OnlySender
        sss = self.baseUrl+str(urlid)+self.seellz+str(see_lz)+self.urlpn+str(1)
#         sss = 'http://tieba.baidu.com/p/3138733512?see_lz=0&pn=1'
        pagecontent = self.getPageContent(sss)

        num = self.decodePageContentNum(pagecontent)

        self.pagenum = num.group(2)  #保存页码数量
        self.title = self.decodeTieziTitle(pagecontent)

        # 删除 title 中不能做文件名的字符
        titleName = self.title.encode('UTF-8')
#        logging.info('titleName is %s' % titleName)
        titleName = titleName.translate(None, b'*|\/<>:"?')
        titleName = titleName.decode('UTF-8')
        logging.info('开始抓取:%s' % titleName)
        logging.info('%s回复贴，共%s页' % (num.group(1),num.group(2)))

        global NewPath
        global Flag_DownloadPics
        global Flag_OnlyPicsUser
        global tiezi
        global TieziKind
        global Deadline

        if Deadline != '':
            deadtime = datetime.datetime.strptime(Deadline, '%Y-%m-%d %H:%M')

        NewPath = './' + str(titleName)

        if not os.path.exists(NewPath):
            os.makedirs(NewPath)

        tiezi.postSum = num.group(1)
        tiezi.pageSum = num.group(2)
        tiezi.title = titleName

        deleteBR = re.compile(r'<br>', re.DOTALL | re.IGNORECASE | re.MULTILINE)
        deleteIMG = re.compile(r'<img.*?>(<br>){0,}', re.DOTALL | re.IGNORECASE | re.MULTILINE)
        picpattern = re.compile('<img.*?class="BDE_Image".*?src="(.*?)".*?>', re.DOTALL | re.IGNORECASE | re.MULTILINE)
        delatpattern = re.compile('<.*?>', re.DOTALL | re.IGNORECASE | re.MULTILINE)

        for i in range(1, int(self.pagenum)+1):#range函数不包括最大的值
            pagecontent = self.getPageContent(\
                self.baseUrl+str(urlid)+self.seellz+str(see_lz)+self.urlpn+str(i))
            logging.info(self.baseUrl+str(urlid)+self.seellz+str(see_lz)+self.urlpn+str(i))
            content = self.decodePageContent(pagecontent, i)

#           ----------------------------------------\n\n楼层：\t\5\nＩＤ：\t\6\n等级：\t\3\n性别：\t\2\n发帖时间：\4\n\n内容：\n\7\n
            for con in content:
                if TieziKind == 0:
                    #获取信息:性别，等级，发帖时间，楼层，ID，发帖内容
                    tmpList = list(con)
                elif TieziKind == 1:
                    #获取信息:楼层，ID，等级，发帖内容，发帖时间
                    tmpList = []
                    tmpList.append(r'0')
                    tmpList.append(con[2])
                    tmpList.append(con[4])
                    tmpList.append(con[0])
                    tmpList.append(con[1])
                    tmpList.append(con[3])
#                logging.debug(swipList)

                # 检查设置的统计截止期
                if Deadline != '':
                    postTime = datetime.datetime.strptime(tmpList[2], '%Y-%m-%d %H:%M')
                    if (deadtime-postTime).total_seconds() < 0:
                        return

                pics = re.findall(picpattern, tmpList[5])
                text = re.sub(deleteIMG, r'', tmpList[5])
                text = re.sub(deleteBR, r'\n', text)
                text = re.sub(delatpattern, r'',text)
                if text == '':
                    tmpList[5] = '无内容'
                else:
                    tmpList[5] = text
                tmpList.append(pics)
#                logging.debug(tmpList)
                tiezi.add(tmpList)
                cnt = int(1)
                if Flag_DownloadPics == 1:    # 下载图片
                    for l in pics:
                        l.split('.')[-1]
                        urllib.request.urlretrieve(l, NewPath + '/Pic[%s][%s楼-%d]_%s.%s' % (tmpList[4], tmpList[3], cnt, tmpList[0], l.split('.')[-1]))
                        cnt += 1

def saveFile(listPrint):
    global NewPath
    global Flag_OnlySender
    global Flag_OnlyPicsUser
    global tiezi
    global Deadline

    if Flag_OnlySender==1:
        f = open(NewPath + '/[帖子内容-楼主].txt','w',encoding='utf-8')
    else:
        f = open(NewPath + '/[帖子内容-全部].txt','w',encoding='utf-8')

    f.write('# %s\n\n' % tiezi.title)
    f.write('%s回复贴，共%s页\n统计结果于本文末尾\n' % (tiezi.postSum, tiezi.pageSum))
    if Flag_OnlyPicsUser == 1:
        f.write('PS：**本文只打印有照片的楼层**\n\n')
    else:
        f.write('PS：**本文打印所有楼层**\n\n')


    staticPicSum = 0
    staticUserSum = 0
    staticJoinSum = 0
    cnt = int(1)

    for tmp in listPrint:
        if Flag_OnlyPicsUser == 1 and tmp[7] == 0:
            staticUserSum += 1
            continue
        f.write('----------------------------------------\n\n## ＩＤ：\t%s\n顺序编号：%d\n' % (tmp[0], cnt))
        cnt += 1
        f.write('性别：\t%s\n' % tmp[1])
        f.write('等级：\t%s\n' % tmp[2])
        f.write('\n### 楼层  贡献%d层\n' % tmp[6])
        f.write('%s\n' % tmp[3])
        f.write('### 文字内容\n%s\n\n' % tmp[4])
#        logging.debug(len(tmp[5]))
        if tmp[7] != 0:
            staticJoinSum += 1
            f.write('### 图片内容 %d 张\n' % tmp[7])
            staticPicSum += tmp[7]
            for l in tmp[5]:
                f.write('![](%s)\n' % l)
        f.write('\n')
        staticUserSum += 1

    # 写入统计信息
    f.write('========================================\n# 统计结果\n\n')
    f.write('### 回复参与人数：%d\n' % staticUserSum)
    f.write('### 爆照参与人数：%d（楼主若发图，也算在里面。根据实际情况减除。）\n' % staticJoinSum)
    f.write('### 收获照片总数：%d\n' % staticPicSum)
    if Deadline == '':
        f.write('### 统计截止日期：%s\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    else:
        f.write('### 统计截止日期：%s\n' % Deadline)
    f.write('========================================\n# 排序结果\n\n')

    # 排序处理
    global Flag_SortedMethod
    # 0. 发图数量 -> 首次回贴时间
    if Flag_SortedMethod == 0:
        listPrint.sort(key=lambda x:x[7], reverse=True)
        f.write('排名先遵循发图总数，再依据第一次回复时间\n\n')
    # 1. 发图数量 -> 贴吧等级
    elif Flag_SortedMethod == 1:
        listPrint.sort(key=lambda x:(x[7],x[2]), reverse=True)
        f.write('排名先遵循发图总数，再依据贴吧等级\n\n')
    # 3. 贴吧等级 -> 发图数量
    elif Flag_SortedMethod == 2:
        listPrint.sort(key=lambda x:(x[2],x[7]), reverse=True)
        f.write('排名先遵循贴吧等级，再依据发图数量\n\n')

    f.write('|  序号  |              ID              | 贴吧等级 |        Info        |\n')
    f.write('| :---: |             :--:             |  :---:  |        :---        |\n')
    for cnt in range(0, len(listPrint)):
        f.write('|  %4d  | %-30s |   %3d   |[%3d图 %3d层 %s]|\n' % (cnt+1, str(listPrint[cnt][0]), listPrint[cnt][2], listPrint[cnt][7], listPrint[cnt][6], listPrint[cnt][1]))
    f.write('\n')
    f.close()
    global Flag_SortedTop
    if Flag_SortedTop != 0:
        f = open(NewPath + '/[Top %d - %d].txt' % (Flag_SortedTop, Flag_SortedMethod),'w',encoding='utf-8')
        if Deadline == '':
            f.write('### 统计截止日期：%s\n' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
        else:
            f.write('### 统计截止日期：%s\n' % Deadline)
        if Flag_SortedMethod == 0:
          f.write('排名先遵循发图总数，再依据第一次回复时间\n\n')
        # 1. 发图数量 -> 贴吧等级
        elif Flag_SortedMethod == 1:
          f.write('排名先遵循发图总数，再依据贴吧等级\n\n')
        # 3. 贴吧等级 -> 发图数量
        elif Flag_SortedMethod == 2:
          f.write('排名先遵循贴吧等级，再依据发图数量\n\n')
        for cnt in range(0, Flag_SortedTop):
            f.write('----------------------------------------\n\n## Top：%d\nＩＤ：\t%s\n' % (cnt+1, listPrint[cnt][0]))
            f.write('性别：\t%s\n' % listPrint[cnt][1])
            f.write('等级：\t%s\n' % listPrint[cnt][2])
            f.write('\n### 楼层  贡献%d层\n' % listPrint[cnt][6])
            f.write('%s\n' % listPrint[cnt][3])
            f.write('### 文字内容\n%s\n\n' % listPrint[cnt][4])
#            logging.debug(len(listPrint[cnt][5]))
            if listPrint[cnt][7] != 0:
                f.write('### 图片内容 %d 张\n' % listPrint[cnt][7])
                for l in listPrint[cnt][5]:
                    f.write('![](%s)\n' % l)
        f.write('\n')

        f.close()

def main():
    global tiezi
    setArgparse()
    tiezi = PostTiezi()
    bdtb = BDTB()
    bdtb.start()
    saveFile(tiezi.contentList)
    logging.info('\n--%s 完成--' % tiezi.title)
    exit()

if __name__ == '__main__':
    main()

