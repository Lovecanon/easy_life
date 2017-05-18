#!/usr/bin/env python
# -*- coding:utf-8 -*-
from .html_to_pdf import HTMLCreator
from .html_to_pdf import BaseCrawler
from .html_to_pdf import abs_url_path
from bs4 import BeautifulSoup


class BSCrawler(BaseCrawler):
    def __init__(self, name, start_url):
        super().__init__(name, start_url)

    def parse_sections(self, resp):
        yield self.start_url

    def parse_body(self, resp):
        soup = BeautifulSoup(resp.content, 'lxml')
        creator = HTMLCreator()
        # parse content
        body = soup.find_all('div', class_='body', role='main')
        if not body:
            raise Exception('No content found!')
        body = body[0]
        creator.add_body(body)

        # parse head's css
        css_tag = soup.find_all('link', rel='stylesheet')
        for c in css_tag:
            creator.add_css(abs_url_path(c['href'], self.start_url))
        return creator.create()


if __name__ == '__main__':
    url = 'http://beautifulsoup.readthedocs.io/zh_CN/latest/#id11'
    BSCrawler('bs', url).run()