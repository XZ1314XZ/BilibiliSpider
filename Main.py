'''
@Author       : XiaoZong
@Since        : 2022-04-02 10:37:24
@LastEditor   : XiaoZong
@LastEditTime : 2022-04-06 00:18:58
@FileName     : Main.py
@Description  : Python爬取Bilibili视频下的评论及回复
'''
import requests
import urllib3
import time
import re
import xlwt
import sqlite3
from segment import segmentword as generate_picture
#屏蔽https证书警告 。urllib3中官方强制验证https的安全证书，如果没有通过是不能通过请求的，虽然添加忽略验证的参数，但是依然会有Warning。
urllib3.disable_warnings()

ua = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.183 Safari/537.36",
}


# 1.获取页面视频oid
def get_oid(BV_CODE: str) -> str:
    # 输入的BV号可带BV可不带，去除BV段即不带
    bv = BV_CODE[2:] if "BV" == BV_CODE[:2] else BV_CODE
    video_url = f"https://www.bilibili.com/video/BV{bv}"
    r = requests.get(video_url, headers=ua, verify=False)
    # raise_for_status()方法，判断网络连接的状态
    r.raise_for_status()
    # 通过视频 bv 号获取 视频oid,标题，返回括号内的内容
    return re.search(r'window.__INITIAL_STATE__={"aid":(\d+)', r.text).group(1), re.search(r'<h1 title="(.*?)"', r.text).group(1)


# 2.获取页面评论数据,每次暂停等待
def get_data(page: int, oid: str):
    time.sleep(sleep_time)  # 暂停等待，减少访问频率，防止IP封禁
    # New,https://api.bilibili.com/x/v2/reply/main?jsonp=jsonp&next=0&type=1&oid=937714725&mode=3&plat=1
    # Old,https://api.bilibili.com/x/v2/reply?jsonp=jsonp&pn=1&type=1&oid=937714725&sort=2
    api_url = "https://api.bilibili.com/x/v2/reply/main?jsonp=jsonp&next={page}&type=1&oid={oid}&mode=3&plat=1&_={ctime}".format(page=page, oid=oid, ctime=int(time.time()))
    print(f'正在处理页面评论:{api_url}')
    r = requests.get(api_url, headers=ua, verify=False)
    r.raise_for_status()
    return r.json()['data']['replies'], r.json()['data']['cursor']['all_count']


# 5.评论中回复多于3条,获取回复数据,每次暂停等待
def get_folded_data(page: int, oid: str, root: int):
    time.sleep(sleep_time)  # 暂停等待，减少访问频率，防止IP封禁
    # https://api.bilibili.com/x/v2/reply/reply?jsonp=jsonp&pn=1&type=1&oid=937714725&ps=20&root=107169517776&_=1649003685857
    url = f'https://api.bilibili.com/x/v2/reply/reply?jsonp=jsonp&pn={page}&type=1&oid={oid}&ps=20&root={root}&_={int(time.time())}'
    print(f'正在处理评论回复:{url}')  # 由于需要减缓访问频率，防止IP封禁，打印访问网址以查看访问进程
    r = requests.get(url, headers=ua, verify=False)
    r.raise_for_status()
    return r.json()['data']


# 4.评论中回复多于3条执行
def loop_folded_reply(root: int, rcount: int):
    # 声明一个数组
    temp = []
    # 定义一个json集合
    temp2 = {}
    # 回复页数，同页面数处理
    end_page = (rcount - 1) // 20 + 1 if (rcount - 1) // 20 + 1 <= pages2 else pages2
    # range中要加1，range不包括结束数
    for page in range(1, end_page + 1):
        data = get_folded_data(page, oid=oid, root=root)
        if not data['replies']:
            continue
        # mid用户uid，rpid当前评论或回复的id同dialog，root为上级评论id同parent(因为只有二级，最顶层的值为0)，count评论顺序，rcount回复数量，like点赞量，ctime时间戳，name用户名，message评论内容
        for item in data['replies']:
            mid = item['mid']
            rpid = item['rpid']
            parent = item['parent']
            dialog = item['dialog']
            like = item['like']
            ctime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item['ctime']))
            name = item['member']['uname']
            emoji_pattern = re.compile(u'[\U00010000-\U0010ffff]')
            message = emoji_pattern.sub('', item['content']['message'])
            message = re.sub(r'\n', '  ', message)
            message = re.sub(r'\t|&#.*?;|回复 @.*? :', '', message)
            message = re.sub(r';', '，', message)
            insert_into(mid, name, message, like, video_title, bv, "1", ctime)


# 3.获取页面评论及回复
def get_reply(data):
    if not data:
        return
    # mid用户uid，rpid当前评论或回复的id同dialog，count评论顺序，rcount回复数量，like点赞量，ctime时间戳，name用户名，message评论内容
    for item in data:
        mid = item['mid']
        rpid = item['rpid']
        rcount = item['rcount']
        like = item['like']
        ctime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item['ctime']))
        name = item['member']['uname']
        emoji_pattern = re.compile(u'[\U00010000-\U0010ffff]')
        message = emoji_pattern.sub('', item['content']['message'])
        message = re.sub(r'\n', '  ', message)
        message = re.sub(r'\t|&#.*?;|回复 @.*? :', '', message)
        message = re.sub(r';', '，', message)

        # 格式化输出日志信息
        if not rcount:
            print('爬取评论回复: User_UID: {0:<10}\t点赞数: {2}\tUSER_Name: {1:<15}'.format(str(mid), name, like), chr(12288))
            insert_into(mid, name, message, like, video_title, bv, "1", ctime)
            continue
        print('爬取评论: User_UID: {0:<10}\t点赞数: {2}\tUSER_Name: {1:<15}'.format(str(mid), name, like), chr(12288))
        insert_into(mid, name, message, like, video_title, bv, "0", ctime)
        # 评论下回复数>0,<3，此函数递归,>3则跳到loop_folded_reply函数。因为评论页面最多显示3条回复，要获取更多回复需要使用回复接口链接
        if 0 < rcount <= 3:
            get_reply(item['replies'])
        elif rcount > 3:
            loop_folded_reply(root=rpid, rcount=rcount)


# 6.生成Excel和SQL的语句
def insert_into(*args):
    global datalist, comments
    # localtime将时间戳转换为当前时区的结构式时间，再由strftime格式化时间
    # 字符串加双引号，默认为int类型
    datalist.append([*args])
    comments.append(args[2])
    f.write(f'INSERT INTO `{bv}`(`uuid`,`uname`,`content`,`likes`,`video_title`,`video_bv`,`isreply`,`time`) VALUES{args};\n')


# 7.导出到数据库
def generate_database(sqlfilename):
    conn = sqlite3.connect('Bilibili_Comment.db')
    # 新建数据库为 Bilibili_Comment.db
    conn = sqlite3.connect('Bilibili_Comment.db')
    # 连接数据库
    cursor = conn.cursor()
    # 使用 cursor() 方法创建一个游标对象 cursor
    with open(sqlfilename, 'r', encoding='utf8') as f:
        data = f.read()
        commands = data.split(';')
        for command in commands:
            try:
                cursor.execute(command)
            except Exception as msg:
                print(msg)
    conn.commit()
    cursor.close()
    conn.close()
    # 关闭连接


# 8.导出到Excel
def generate_excelfile(excelfilename):
    # 创建excel表格类型文件
    book = xlwt.Workbook(encoding='utf-8', style_compression=0)
    # 在excel表格类型文件中建立一张sheet表单
    sheet = book.add_sheet('Bilibili_Comment', cell_overwrite_ok=True)
    # 自定义列名
    col = ('用户ID', '用户名', '评论内容', '点赞量', '视频标题', '视频BV号', '评论0回答1', '发布时间')

    sheet.row(0).height_mismatch = True
    sheet.row(0).height = 20 * 20  #20为基准数，20为20磅
    # 设置样式,对齐,列表宽度,256为基准数，后面是字符长度
    sheet.col(0).width = 256 * 12
    sheet.col(1).width = 256 * 20
    sheet.col(2).width = 256 * 95
    sheet.col(3).width = 256 * 8
    sheet.col(4).width = 256 * 25
    sheet.col(5).width = 256 * 14
    sheet.col(6).width = 256 * 10
    sheet.col(7).width = 256 * 22
    style = xlwt.XFStyle()  # 创建一个样式对象，初始化样式
    alignment = xlwt.Alignment()  # 创建 对齐样式Alignment
    alignment.horz = 0x02  # 设置水平居中,左中右分别1,2,3
    alignment.vert = 0x01  # 设置垂直居中,上中下分贝0,1,2
    style.alignment = alignment  # 添加 对齐样式Alignment to 样式
    style1 = xlwt.XFStyle()  # 创建一个样式对象，初始化样式
    alignment1 = xlwt.Alignment()  # 创建 对齐样式Alignment
    alignment1.horz = 0x01  # 设置水平居中,左中右分别1,2,3
    alignment1.vert = 0x01  # 设置垂直居中,上中下分贝0,1,2
    style1.alignment = alignment1  # 添加 对齐样式Alignment to 样式
    # 将列属性元组col写进sheet表单中
    for i in range(0, 8):
        sheet.write(0, i, col[i], style)
    # 写入数据
    for i in range(0, len(datalist)):
        sheet.row(i + 1).height_mismatch = True
        sheet.row(i + 1).height = 20 * 18  #20为基准数，18为18磅
        data = datalist[i]
        print("正在写入到Excel:  ", data)
        for j in range(0, 8):
            if j == 2:
                sheet.write(i + 1, j, data[j], style1)
                continue
            sheet.write(i + 1, j, data[j], style)
    # 保存为Excel文件
    savepath = f'{excelfilename}'
    book.save(savepath)


# 9.导出到txt
def generate_txt(txtfilename):
    for comment in comments:
        with open(txtfilename, 'a', encoding='utf-8') as f:
            f.write(f'{comment}\n')


if __name__ == '__main__':
    pages1 = int(input('请输入爬取"视频评论"的页数(每页至多20条):'))
    pages2 = int(input('请输入爬取"评论回复"的页数(每页至多20条):'))
    # https://www.bilibili.com/video/BV1xT4y1e73P,视频播放页面,链接最后的值
    bv = str(input('请输入视频的BV号(如BV1xT4y1e73P):'))
    datalist = []
    comments = []
    begin_time = time.time()
    # 每次调用链接后的休息时间,访问网页间隔，防止IP被禁，若运行程序后出现无法访问评论区的现象，等待2小时即可
    sleep_time = 1
    oid, video_title = get_oid(bv)
    # 新建一个表，没必要设置主键，同一个人可以发多条主键不唯一
    sql = f'''create table {bv}(
        uuid INT(12) NOT NULL,
        uname TEXT,
        content TEXT,
        likes VARINT,
        video_title TEXT,
        video_bv VARCHAR,
        isreply INT,
        time VARCHAR);\n'''
    # strftime第二个参数不加默认是当前时间
    nowtime = time.strftime("%Y-%m-%d_%H-%M-%S")
    sqlfilename = f'{nowtime}.sql'
    excelfilename = f'{nowtime}.xlsx'
    txtfilename = f'{nowtime}.txt'
    f = open(f'{sqlfilename}', 'w', encoding='utf-8')
    f.write(sql)

    page = 1
    while True:
        try:
            # 预处理数据，提取主要键值
            data, reply_num = get_data(page, oid)
            # 遍历所有回复，核心函数
            get_reply(data)
            # 最后一页不足20条，"//"取整除。超出最大页按最大页
            end_page = (reply_num - 1) // 20 + 1 if (reply_num - 1) // 20 + 1 <= pages1 else pages1
            if page == end_page:
                break
            page += 1
        except Exception as e:
            print('ERROR:', e)
            print('退出循环 结束')
            break
    f.close()
    generate_excelfile(excelfilename)
    generate_database(sqlfilename)
    generate_txt(txtfilename)
    generate_picture(txtfilename)
    end_time = time.time()
    run_time = end_time - begin_time
    print('本次运行时间：', '{:.2f}'.format(run_time), 's')
