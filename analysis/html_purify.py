# -*- coding: utf-8 -*-
# __author__ = 'Jianghua Zhao'
# jianghua.zhao@socialcredits.cn

import bs4
import sys
import re
reload(sys)
sys.setdefaultencoding('utf-8')


def build_beautifulsoup(html):
    """
    将html文档封装成BeautifulSoup对象
    :param html: 输入文档
    :return:
    """
    return bs4.BeautifulSoup(html, "html.parser")


def purify_navistring_attr(tag):
    """
    精简标签的文本信息以及标签属性
    1: 删除标签文档中的注释
    2: 删除标签文本前后的空白字符
    3: 删除标签中的属性
    4: 保留<table>标签中的 "colspan" 和 "rowspan"属性, 用于后面对表格的分析
    :param tag: 待处理标签
    :return:
    """
    for child in tag.children:
        if isinstance(child, bs4.Comment):  # 删除标签文档中的注释
            child.extract()
        elif isinstance(child, bs4.NavigableString):  # 删除标签文本前后的空白字符
            child.replace_with(child.strip().replace(u"？", u" "))
        elif isinstance(child, bs4.Tag):
            if child.name in ("td", "th"):  # 保留表格中的 "colspan" 和 "rowspan"属性
                t = {}
                if "colspan" in child.attrs:
                    t["colspan"] = child["colspan"]
                if "rowspan" in child.attrs:
                    t["rowspan"] = child["rowspan"]
                child.attrs = t
            else:
                child.attrs = None  # 删除标签中的属性
            purify_navistring_attr(child)


def purify_tags(tag):
    """
    精简标签中的子标签
    1: 删除没有实际内容的标签
    2: 删除不显示的标签, 如<style>、<script>
    3: 展开不自动分段的标签， 如<span>、<strong>
    4: 删除不显示的标签, display:none
    :param tag:  待处理标签
    :return:
    """
    contents = [cld for cld in tag.contents]
    for child in contents:
        if not isinstance(child, bs4.Tag):
            continue

        if len(child.get_text().strip()) <= 0:  # 删除没有实际内容的标签
            if child.name not in ("br", "hr", "th", "td"):  # 保留br标记用作后面的分段
                child.extract()

        elif child.name in ("style", "script", "link"):  # 删除不显示的标签, 如<style>、<script>等
            child.extract()

        elif child.name in ("span", "strong", "b", "u", "a", "abbr", "acronym", "area", "base",
                            "bdi", "bdo", "del", "i", "q", "label") \
                or child.name.startswith("fmt") or ":" in child.name:  # 展开<span>,<strong>,<b>等不换行的标签
            if len(child.find_all(lambda t: t.name in ("div", "p"))):  # 如果标签里面还有自动分段的标签就跳过
                purify_tags(child)
            else:
                child.insert_before(child.get_text().strip())
                child.extract()

        else:
            purify_tags(child)


def purify_none_display_tag(tag):
    """
    删除没有显示的标签
    :param tag:
    :return:
    """
    contents = [cld for cld in tag.contents]

    for child in contents:
        if not isinstance(child, bs4.Tag):
            continue
        if child.attrs is not None and child.attrs.get("style") is not None:
            styles = child.attrs.get("style").strip().split(";")
            styles = [[y.strip() for y in x.split(":")] for x in styles if ":" in x]
            styles = [x for x in styles if len(x) == 2 and x[0] == u'display' and x[1] == u'none']
            if len(styles) > 0:  # 删除 display:none 的标签
                child.extract()
                continue
        purify_none_display_tag(child)


def find_table_pattern(tag):
    """
    从html文本中发现表格模式
    :param tag:
    :return:
    """
    pass


def fix_table(tag):
    """
    将table转成标准样式<tr><td></td></tr>
    :param tag:
    :return:
    """
    contents = [cld for cld in tag.contents]

    for child in contents:
        if not isinstance(child, bs4.Tag):
            continue
        if child.name == "table":
            conts = []
            for i, cont in enumerate(child.contents):
                if isinstance(cont, bs4.Tag):
                    conts.append(cont)
            if len(conts) == 1 and conts[0].name == "tbody":
                child = conts[0]

            st, wr = 0, False
            conts = [cont for cont in child.contents]
            for i, cont in enumerate(conts):
                if not isinstance(cont, bs4.Tag):
                    continue
                if cont.name == "tr":
                    if wr:
                        tr = build_beautifulsoup("<tr></tr>").tr
                        for ct in conts[st:i]:
                            t = ct.extract()
                            tr.append(t)
                        cont.insert_before(tr)
                        wr = False
                    st = i + 1
                else:
                    wr = True

    for child in tag.contents:
        if not isinstance(child, bs4.Tag):
            continue
        fix_table(child)


def purify_html(html):
    """
    精简html文档，使文档结构清晰，方便分析
    :param html:  输入html文档
    :return:
    """
    html = unicode(html)
    html = re.sub(u"\n", u"", html)
    html = re.sub(u"<link .*?(:? /|)>", u"", html)
    html = re.sub(u"<script.*?>[\s\S]*?</script>", u"", html)
    html = re.sub(u"<style.*?>[\s\S]*?</style>", u"", html)
    html = re.sub(u"<!\-\-[\s\S]*?\-\->", u"", html)
    html = re.sub(u"<\??xml:namespace[\s\S]*?/\??>", u"", html)
    html = re.sub(u"\*{10,}", u";", html)
    html = re.sub(u"\*{3,10}", u"", html)

    unexp_strs = re.findall(ur"\\frame\\ewebeditor\\uploadfile\\", html)
    if len(unexp_strs) >= 50:
        html = u"<html><body><div></div></body></html>"

    bs = build_beautifulsoup(html)
    purify_none_display_tag(bs)
    purify_navistring_attr(bs)
    purify_tags(bs)
    fix_table(bs)

    return str(bs)
