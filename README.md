# TiebaCrawler

Use Tieba post ID to get post information

* 本代码基于 Python 3.5.2 编写
* 最新脚本 Windows 下测试通过，MacOS 基于 python3 测试通过

## 简要说明

两个脚本文件

```
launcher.py
TiebaCrawler.py
```

- **launcher.py**

该脚本里面可以自己定义任务，运行该脚本可以自动抓取多个内部定义好的帖子。

任务添加方法如下：

```
    # '4842388571', '0', '2016-11-12', '00:00', '20', '0', '0', '0', '1'
    # 1: 帖子ID：在地址栏可以找到
    # 2: 帖子种类：0 大部分帖子 1 达音科吧帖子
    # 3: 该时间以后的帖子不统计
    # 4: 该时间以后的帖子不统计
    # 5: Top N 排名前N位。0 表示不排序
    # 6: 排序方法
    #       0 发图数量 -> 首次回贴时间
    #       1 发图数量 -> 贴吧等级
    #       2 贴吧等级 -> 发图数量
    # 7: 1 只看楼主；2 全部帖子
    # 8: 1 只保存有图片的楼层；0 保存所有回复楼层
    # 9: 1 下载图片；0 不下载图片
    TieziList = [
                ['4842388571', '0', '2016-11-12', '00:00', '20', '0', '0', '0',     '1'], # 国砖吧cayin爆照贴
                ['4836451867', '1', '2016-11-12', '00:00', '20', '1', '0', '0',     '0'], # 达音科双11第二轮活动贴
    ]
```

- **TiebaCrwaler.py**

所有抓取网页以及输出结果的代码都在该文件中，代码管用，没设计，勿喷。。。

需要通过命令行传送参数执行：

```
python TiebaCrawler.py --ID 4842388571 --TieziKind 0 --Date 2016-11-12 --Time 00:00 --SortedTop 20 --SortedMethod 0 --OnlySender 0 --OnlyPicsUser 0 --DownloadPics 0
```

---
### 2016/11/09 更新

MacOS + Python3 测试通过  
CodeRunner 和 Sublime 均调试通过

1. `launcher.py` 加入系统类型判断
2. 选择合适的 python 命令行

---
### 2016/11/08 更新

Windows 下测试通过，MacOS 未测试

1. 加入launcher
2. TiebaCrawler.py 改造为命令行传输参数