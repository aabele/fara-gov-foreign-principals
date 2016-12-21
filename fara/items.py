# -*- coding: utf-8 -*-
"""
Scraped data item models
"""

import scrapy


class FaraItem(scrapy.Item):
    """
    Foreign principal details
    """
    url = scrapy.Field()
    reg_num = scrapy.Field()
    country = scrapy.Field()
    state = scrapy.Field(default=None)
    address = scrapy.Field()
    foreign_principal = scrapy.Field()
    registrant = scrapy.Field()
    exhibit_urls = scrapy.Field(default=[])
    date = scrapy.Field(serializer=str)
