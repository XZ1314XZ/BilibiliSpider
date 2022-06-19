'''
@Author       : XiaoZong
@Since        : 2020-02-13 22:46:18
@LastEditor   : XiaoZong
@LastEditTime : 2022-04-06 00:26:14
@FileName     : segment.py
@Description  : 分词并组成词云
'''
# coding:utf-8
import jieba
import numpy
import codecs
import pandas
from wordcloud import WordCloud
from imageio import imread
# import matplotlib.pyplot as plt

global txtfilename


def load_file_segment(txtfilename):
    # 读取文本文件并分词
    jieba.load_userdict("./Dependence/mywords.txt")
    # 加载我们自己的词典
    f = codecs.open(f"{txtfilename}", 'r', encoding='utf-8')
    # 打开文件
    content = f.read()
    # 读取文件到content中
    f.close()
    # 关闭文件
    segment = []
    # 保存分词结果
    segs = jieba.cut(content)
    # 对整体进行分词
    for seg in segs:
        if len(seg) > 1 and seg != '\r\n':
            # 如果说分词得到的结果非单字，且不是换行符，则加入到数组中
            segment.append(seg)
    return segment


def get_words_count_dict(txtfilename):
    segment = load_file_segment(txtfilename)
    # 获得分词结果
    df = pandas.DataFrame({'segment': segment})
    # 将分词数组转化为pandas数据结构
    stopwords = pandas.read_csv("./Dependence/stopwords.txt", index_col=False, quoting=3, sep="\t", names=['stopword'], encoding="utf-8")
    # 加载停用词
    df = df[~df.segment.isin(stopwords.stopword)]
    # 如果不是在停用词中
    words_count = df.groupby(by=['segment'])['segment'].agg([("计数", numpy.size)])
    # 按词分组，计算每个词的个数
    words_count = words_count.reset_index().sort_values(by="计数", ascending=False)
    # reset_index是为了保留segment字段，排序，数字大的在前面
    return words_count


def random_color_func(word=None, font_size=None, position=None, orientation=None, font_path=None, random_state=None):
    h = int(360.0 * 45.0 / 255.0)
    s = int(100.0 * 255.0 / 255.0)
    l = int(100.0 * float(random_state.randint(60, 120)) / 255.0)

    return "hsl({}, {}%, {}%)".format(h, s, l)


def segmentword(txtfilename):
    words_count = get_words_count_dict(txtfilename)
    # 获得词语和频数

    bimg = imread('./Dependence/bili.jpg')

    wordcloud = WordCloud(
        background_color='white',
        mode='RGBA',
        mask=bimg,
        font_path='simhei.ttf',
        color_func=random_color_func,
        random_state=50,
    )

    words = words_count.set_index("segment").to_dict()
    # 将词语和频率转为字典
    wordcloud = wordcloud.fit_words(words["计数"])
    #保存图片
    wordcloud.to_file("Bili_wordcloud.png")
    """
    # 将词语及频率映射到词云对象上
    bimgColors = ImageColorGenerator(bimg)
    # 生成颜色
    plt.axis("off")
    # 关闭坐标轴
    plt.imshow(wordcloud.recolor(color_func=bimgColors))
    #保存图片 注意 在show()之前  不然show会重新创建新的 图片
    plt.savefig("result.png", dpi=100)
    # 显示图片
    plt.show()
    """
