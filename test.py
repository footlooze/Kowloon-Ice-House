# -*- coding: utf-8 -*-
__author__ = 'peter'

from string import Template
import scrapemark
import logging

page_url_template=Template('http://www.zuche.com/jsp/convenience/convenienceIndex.page?mid=81171&cid=81167&page=${page}')
host_url='http://www.zuche.com/'
HTTP_DATE_FMT = '%Y-%m-%d'

def deals():
    pages=(page_url_template.substitute(page=str(i)) for i in range(1, 21,1))
    for url in pages:
        for deal in scrapemark.scrape("""
        <ul class="contnwlst">
        {*
            <li>
                <div>
                    <a href="{{ [deals].url }}">{{ [deals].title }}</a>
                </div>
                <span class="floatrgt">{{ [deals].date }}</span>
            </li>
        </ul>
        *}
        """, url=url)['deals']:
            yield deal

def crawl():
    for deal in ({'url':host_url+deal['url'], 'title':deal['title'], 'date':deal['date']} for deal in deals()):
        process()

def process():
    proposition=scrapemark.scrape("""
        <div class="sfc_news_txt">
            <a>{{ deal.from_shop}}</a>
            <a>{{ deal.to_shop}}</a>
            2、指定车型：<span id="modeName1">{{ deal.car_spec }}</span>   {{ deal.inventory }}
            3、可租区间： {{ deal.available_date }}至 {{ deal.expire_date }}；
        </div>
        <table class="sfc_tab">
          <tr class="sfc_news_text">
            <td>{{ deal.from_city }}—{{ deal.to_city }}</td>
            <td>{{ deal.days_allowed|int }}天</td>
            <td>{{ deal.mileages_allowed|int }}公里</td>
            <td>{{ deal.gps }}</td>
            <td>{{ deal.baby_seat }}</td>
            <td>{{ deal.listed_price|int }}元</td>
            <td>{{ deal.discount_price|int }}元</td>
            <td>{{ deal.toll }}</td>
          </tr>
        </table>
        """, url='http://www.zuche.com//order/ConvenienceInfoControl.do_?convenienceId=10392&mid=81171&cid=81167')['deal']
    logging.warning(proposition)

if __name__ == '__main__':
    process()
