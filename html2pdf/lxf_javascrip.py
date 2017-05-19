#!/usr/bin/env python
# -*- coding:utf-8 -*-
from html2pdf import html_to_pdf
from bs4 import BeautifulSoup


class NodeCrawler(html_to_pdf.BaseCrawler):
    def parse_sections(self):
        """
            处理多个页面生成一个pdf
        :param resp:
        :return: 要处理页面的url
        """
        for u in self.start_urls:
            resp = self.do_get(u)
            soup = BeautifulSoup(resp.content, 'lxml')
            menu_tag = soup.find_all(class_='uk-nav-side')[1]
            for li in menu_tag.find_all('li'):
                section_url = li.a.get('href')
                if not section_url.startswith('http'):
                    section_url = ''.join([self._get_domain(u), section_url])  # 补全为全路径
                yield section_url

    def parse_body(self, url):
        soup = BeautifulSoup(self.do_get(url), 'lxml')
        creator = html_to_pdf.HTMLCreator()
        # parse content
        body = soup.find_all('div', class_='x-wiki-content')

        if not body:
            raise Exception('No content found!')
        body = body[0]
        # delete video tag
        while body.video:
            body.video.extract()

        # change relative image url to absolute url
        imgs = body.find_all('img')
        for i in imgs:
            i['src'] = html_to_pdf.abs_url_path(i['src'], url)

        # add title
        center_tag = soup.new_tag('center')
        title_tag = soup.new_tag('h1')
        title_tag.string = soup.find('h4').get_text()
        center_tag.insert(1, title_tag)
        body.insert(1, center_tag)

        creator.add_body(body)
        # parse head's css
        css_tag = soup.find_all('link', rel='stylesheet')
        for c in css_tag:
            creator.add_css(html_to_pdf.abs_url_path(c['href'], url))
        return creator.create()


if __name__ == '__main__':
    url = 'http://www.liaoxuefeng.com/wiki/001434446689867b27157e896e74d51a89c25cc8b43bdb3000'
    NodeCrawler('javascript', url, pre_download_img=True, delete_html_file=False).run()
