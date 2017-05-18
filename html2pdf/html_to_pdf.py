#!/usr/bin/env python
# -*- coding:utf-8 -*-
from bs4 import BeautifulSoup
from bs4 import Tag
import requests
import pdfkit
import time
import os
import re
import hashlib
import shutil

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.81 Safari/537.36'
}
OPTIONS = {
    'page-size': 'Letter',
    'margin-top': '0.5in',  # 距离上边框的距离
    'margin-right': '0.2in',
    'margin-bottom': '0.5in',
    'margin-left': '0.2in',
    'encoding': "UTF-8",
    'custom-header': [
        ('Accept-Encoding', 'gzip,deflate,sdch'),
        ('User-Agent',
         'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 7Star/2.0.56.2 Safari/537.36'),
        ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'),
    ],
    'outline-depth': 10,
    # 'javascript-delay': '5000',
    'quiet': '',
}

HTML_TEXT = '!DOCTYPE html><html lang="en"><head>{head}</head><body>{body}</body></html>'
HEAD_META = '<meta charset="{encoding}">'
HEAD_CSS = '<link rel="stylesheet" href="{css_uri}">'


class HTMLCreator(object):
    def __init__(self, encoding='UTF-8'):
        self.css_links = []
        self.body = ''
        self.soup = None
        self.encoding = encoding

    def add_css(self, link):
        self.css_links.append(link)

    def add_body(self, body):
        self.body = body

    def create(self):
        """
            如果传入的content是Tag类型直接插入body标签内
            如果传入的content是str类型进行字符串拼接
        :return: 返回组装好的html字符串
        """
        if isinstance(self.body, Tag):
            self.soup = BeautifulSoup('<!DOCTYPE html>', 'lxml')
            html_tag = self.soup.new_tag('html', lang='en')
            # head
            head_tag = self.soup.new_tag('head')
            meta_tag = self.soup.new_tag('meta', charset=self.encoding)
            head_tag.append(meta_tag)
            for c in self.css_links:
                head_tag.append(self.soup.new_tag('link', rel='stylesheet', href=c))
            html_tag.append(head_tag)
            # body
            body_tag = self.soup.new_tag('body')
            body_tag.append(self.body)
            html_tag.append(body_tag)
            self.soup.append(html_tag)
            return str(self.soup)
        else:
            if isinstance(self.body, bytes):
                self.body = self.body.decode(self.encoding)
            head = HEAD_META.format(encoding=self.encoding)
            for c in self.css_links:
                head += HEAD_CSS.format(css_uri=c)
            return HTML_TEXT.format(head=head, body=self.body)


class BaseCrawler(object):
    def __init__(self, name, start_url, pre_download_img=False, delete_html_file=False):
        """
            爬虫的基类
        :param name: 爬虫名字
        :param start_url: 开始url
        :param pre_download_img: 是否预下载页面中包含的图片
        :param delete_html_file: 生成pdf后是否将html文件删除
        """
        self.name = name
        self.start_url = start_url
        self.pre_download_img = pre_download_img
        self.delete_html_file = delete_html_file
        # ParseResult(scheme='http', netloc='www.baidu.com', path='', params='', query='', fragment='')
        self.domain = '{uri.scheme}://{uri.netloc}'.format(uri=requests.utils.urlparse(self.start_url))

        if not os.path.exists(self.name):
            os.mkdir(self.name)

    def parse_sections(self, resp):
        """
            如果只是将一个页面转成pdf，则直接返回self.start_url即可
        :param resp:
        :return:
        """
        raise NotImplementedError

    def parse_body(self, resp):
        """
            处理要生成pdf的页面
        :param resp:
        :return: 返回处理后的html字符串
        """
        raise NotImplementedError

    def do_get(self, url, headers=HEADERS, timeout=20):
        """
            http的get请求，重试一次
        :param url: 请求地址
        :param headers: 请求头
        :param timeout: 超时
        :return:
        """
        for i in (0, 1):
            try:
                resp = requests.get(url, headers=headers, timeout=timeout)
                if resp.ok:
                    return resp
                else:
                    raise Exception('Request [%s] error, code %d' % (url, resp.status_code))
            except Exception as e:
                time.sleep(5)
                if i:
                    raise

    def download_img(self, html):
        """
            预下载网页中图片，防止所有同时下载服务器无反应
        :param html: html文档
        :return: html， 其中图片地址替换成本地图片地址
        """
        img_pattern = "<img .*?src=\"(\S*?)\""
        m = re.findall(img_pattern, html)
        for img_url in m:
            img_data = self.do_get(img_url)
            hash_md5 = hashlib.md5(img_url.encode('utf-8'))
            img_dir = os.path.join(self.name, 'static', 'img')
            if not os.path.exists(img_dir):
                os.makedirs(img_dir)
            img_name = hash_md5.hexdigest() + '.jpg'
            with open(os.path.join(img_dir, img_name), 'wb') as f:
                f.write(img_data.content)
            html = html.replace(img_url, os.path.join('static', 'img', img_name))
        time.sleep(3)
        return html

    def run(self):
        start = time.time()
        print('Start to crawl...')
        html_files = []
        resp = self.do_get(self.start_url)

        for index, url in enumerate(self.parse_sections(resp)):
            html = self.parse_body(self.do_get(url))
            if self.pre_download_img:
                html = self.download_img(html)
            f_path = os.path.join(self.name, '.'.join([str(index), 'html']))
            # with open(f_path, 'wb') as f:
            #     html = html if isinstance(html, bytes) else html.encode('utf-8')
            #     f.write(html)
            html_files.append(f_path)

        try:
            print('Start to convert html to pdf')
            # https://wkhtmltopdf.org/downloads.html
            # 如果wkthmltopdf不在path环境变量中，则指定该文件的路径
            # 内部实现是通过命令行生成pdf
            path_wkthmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
            config = pdfkit.configuration(wkhtmltopdf=path_wkthmltopdf)
            pdfkit.from_file(html_files, self.name + '.pdf', options=OPTIONS, configuration=config)
        except Exception as e:
            print('Convert fail {}'.format(e))
        finally:
            if self.delete_html_file:
                shutil.rmtree(self.name)
            total_time = time.time() - start
            print('Spend time: {:.2f}s'.format(total_time))


class PageCrawler(BaseCrawler):
    def __init__(self, name, start_url, body_tag_name, pre_download_img=True, delete_html_file=False, **body_tag_attrs):
        """
            将一个HTML页面转成pdf可以如此简单
            url = 'https://cs231n.github.io/convolutional-networks/'
            body_tag_attrs = {'class': 'post'}
            PageCrawler('convolutional-networks', url, body_tag_name='div', **body_tag_attrs).run()
        :param name: 页面名称
        :param start_url: 页面url
        :param body_tag_name: 所要保存成pdf的html标签名
        :param body_tag_attrs: 所要保存成pdf的html标签属性
        """
        super().__init__(name, start_url, pre_download_img, delete_html_file)
        self.body_tag_name = body_tag_name

        if 'class' in body_tag_attrs.keys():
            body_tag_attrs['class_'] = body_tag_attrs['class']
            body_tag_attrs.pop('class')
        self.body_tag_attrs = body_tag_attrs

    def parse_sections(self, resp):
        yield self.start_url

    def parse_body(self, resp):
        soup = BeautifulSoup(resp.content, 'lxml')
        creator = HTMLCreator()
        # parse content
        body = soup.find_all(self.body_tag_name, **self.body_tag_attrs)
        if not body:
            raise Exception('No content found!')
        body = body[0]
        creator.add_body(body)

        # parse head's css
        css_tag = soup.find_all('link', rel='stylesheet')
        for c in css_tag:
            creator.add_css(abs_url_path(c['href'], self.start_url))
        return creator.create()


def abs_url_path(rel_url, base_url):
    """
        将href路径转成绝对路径
    :param rel_url: 相对路径
    :param base_url: start_url
    :return: 链接的绝对路径
    """
    if rel_url.startswith('http'):
        return rel_url
    u = requests.utils.urlparse(base_url)
    url_scheme = u.scheme
    url_net_loc = u.netloc
    url_path = u.path[:-1] if u.path.endswith('/') else u.path[: u.path.rindex('/')]
    if rel_url.startswith('/'):
        return '%s://%s%s' % (url_scheme, url_net_loc, rel_url)
    else:
        return '%s://%s%s/%s' % (url_scheme, url_net_loc, url_path, rel_url)

if __name__ == '__main__':
    url = 'http://www.cnblogs.com/ooon/p/5603869.html'
    body_tag_attrs = {'class': 'post'}
    PageCrawler('convolutional-networks', url, body_tag_name='div', **body_tag_attrs).run()