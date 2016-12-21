# -*- coding:utf8 -*-
"""
www.fara.gov spider
"""

from __future__ import unicode_literals

from datetime import datetime

from scrapy import Spider, Request
from scrapy.exceptions import CloseSpider
from scrapy.http import FormRequest
from scrapy.selector import Selector

from fara import items


class ForeignPrincipalSpider(Spider):
    """
    Scrapes foreign principal details
    """
    name = 'foreign-principals'

    start_urls = [
        'https://www.fara.gov/quick-search.html'
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'FEED_URI': 'items.json',
        'FEED_FORMAT': 'json',
    }

    pager_backend_url = 'https://efile.fara.gov/pls/apex/wwv_flow.show'

    items_per_page = 15

    url_key_name = 'first_page_url'

    # -- Data manipulation utilities --

    @staticmethod
    def _patch_dictionary(source, destination):
        """
        Copy over items from source dict to destination dict

        :param source: dictionary
        :param destination: dictionary
        :return: merged dictionary
        """
        data = destination.copy()
        data.update(source)
        return data

    def _get_reload_request_headers(self, extra_headers=None):
        """
        Update default request headers

        :param extra_headers: dict or None
        :return: merged dictionary|dict
        """
        return self._patch_dictionary(extra_headers or {}, {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'efile.fara.gov',
            'Origin': 'https://efile.fara.gov',
        })

    def _get_reload_request_formdata(self, extra_data=None):
        """
        Update default form values

        :param extra_data: dict or None
        :return: merged dictionary|dict
        """
        return self._patch_dictionary(extra_data or {}, {
            'p_request': 'APXWGT',
            'p_flow_id': '171',
            'p_flow_step_id': '130',
            'p_widget_num_return': '15',
            'p_widget_name': 'worksheet',
            'p_widget_mod': 'ACTION',
            'p_widget_action': 'PAGE',

            'x01': '80340213897823017',
            'x02': '80341508791823021',
            'p_instance': '9939816130573',
        })

    @staticmethod
    def _to_datetime(date_string):
        """
        Convert mm/dd/yyyy into datetime.datetime() object.
        This one should be moved to loader

        :param date_string: date string
        :return: return datetime
        """
        return datetime.strptime(date_string, '%m/%d/%Y')

    # -- Scraping utilities --

    def _get_pages_total(self, response):
        """
        Calculate total page count

        :param response: scrapy response object
        :return: calculated page count|int
        """
        el = Selector(response).xpath('//td[@class="pagination"]//span[@class="fielddata"]/text()').extract_first()
        total = int(el.split('of')[1].strip()) / self.items_per_page
        self.logger.debug("Total pages: %s", total)
        return int(total)

    def _has_next_page(self, response):
        """
        Check if page has pagination block and links to the next page

        :param response: scrapy response object
        :return: Boolean
        """
        has = Selector(response).xpath('//td[@class="pagination"]//img[@title="Next"]').extract_first() is not None
        self.logger.debug("Has next page: %s", has)
        return has

    @staticmethod
    def _parse_column(row, column_id, column_action='/text()', delimiter=' ', test_mode=False):
        """
        Parse value out of table column

        :param row: row element
        :param column_id: column identificator
        :param delimiter: blank space or comma - br's will be replaced with it
        :return: column text|str
        """

        # The only reason for this is possibility to fake response in unittests
        base = Selector(row) if test_mode else row

        el = delimiter.join(base.xpath('.//td[@headers="%s"]%s' % (column_id, column_action)).extract())
        el = el.replace(u'\u00a0', ' ')
        el = el.strip()
        return el or None

    @staticmethod
    def _get_input_value(response, element_id):
        """
        Find form element by ID and get value

        :param response: scrapy response object
        :param element_id: element id value|str
        :return: element value attribute value|str
        """
        return Selector(response).xpath('//input[@id="%s"]/@value' % element_id).extract_first()

    # -- Scrapy callbacks --

    def _get_exhibit_urls(self, response):
        """
        Get exhibit document urls.

        :param response: scrapy response object
        """
        key = 'exhibit_urls'
        item = response.meta.get('item')
        item[key] = []
        for url in response.xpath('//div[@id="apexir_DATA_PANEL"]//a/@href').extract():
            item[key].append(response.urljoin(url))
            self.logger.debug('Found exhibit url %s', item[key])

        yield item

        if self._has_next_page(response):
            self.logger.debug("Has link to the next page")
            # Apparently there are no exhibit doc pages with more than
            # 15 documents so i'm not going to waste time on this...
            raise CloseSpider('Found multi page doc pages')

    def _get_pager_params(self, page):
        """
        Generate form pager field value

        :param page:
        :return:
        """
        self.logger.debug("Calculating pager params for page: %s" % page)
        data = 'pgR_min_row=%smax_rows=%srows_fetched=%s' % (
            page * self.items_per_page + 1, self.items_per_page, self.items_per_page
        )
        self.logger.debug(data)
        return data

    def _parse_page_results(self, response):
        """
        Parse data rows from the index page table. If page has link to the next page, current method will be
        run recursively.

        :param response: scrapy response object
        """
        page_id = response.meta.get('page_id')

        rows = Selector(response).xpath('//table[@class="apexir_WORKSHEET_DATA"]//tr[@class="odd" or @class="even"]')
        self.logger.debug('Found %s rows', len(rows))

        for row in rows:

            item = items.FaraItem()

            item_url = response.urljoin(row.xpath('.//td[@headers="LINK"]/a/@href').extract_first())

            item['registrant'] = self._parse_column(row, 'REGISTRANT_NAME')
            item['date'] = self._to_datetime(self._parse_column(row, 'FP_REG_DATE'))
            item['foreign_principal'] = self._parse_column(row, 'FP_NAME')

            # Address without linebreaks
            item['address'] = self._parse_column(row, 'ADDRESS_1', '[normalize-space()]/text()')

            if not item['address']:
                # Address with linebreaks
                item['address'] = self._parse_column(row, 'ADDRESS_1',
                                                     '[normalize-space()]/text()[following-sibling::br or '
                                                     'preceding-sibling::br]', delimiter=', ')

            item['reg_num'] = self._parse_column(row, 'REG_NUMBER')
            item['state'] = self._parse_column(row, 'STATE')
            item['country'] = self._parse_column(row, 'COUNTRY_NAME')
            item['url'] = item_url

            yield Request(item_url, callback=self._get_exhibit_urls, meta={'item': item}, dont_filter=True)

        if self._has_next_page(response):
            self.logger.debug("Has link to the next page")

            url = response.request.url
            if url == self.pager_backend_url:
                url = response.meta.get(self.url_key_name)

            meta = {}
            meta['page_id'] = page_id + 1
            meta[self.url_key_name] = url
            meta['p_instance'] = response.meta.get('p_instance')

            header_vars = self._get_reload_request_headers({
                'Referer': url,
            })

            form_vars = self._get_reload_request_formdata({
                'p_instance': response.meta.get('p_instance'),
                'x01': self._get_input_value(response, 'apexir_WORKSHEET_ID'),
                'x02': self._get_input_value(response, 'apexir_REPORT_ID'),
                'p_widget_action_mod': self._get_pager_params(page_id),
            })

            yield FormRequest(self.pager_backend_url,
                              method='POST',
                              headers=header_vars,
                              formdata=form_vars,
                              callback=self._parse_page_results,
                              meta=meta,
                              dont_filter=True)

    def _toggle_country_column(self, response):
        """
        Simulate the click on `Country/Location Represented` checkbox.

        :param response: scrapy response object
        """

        url = response.request.url
        if url == self.pager_backend_url:
            url = response.meta.get(self.url_key_name)

        meta = {}

        meta[self.url_key_name] = url

        header_vars = self._get_reload_request_headers({
            'Referer': url,
        })

        p_instance = self._get_input_value(response, 'pInstance')
        meta['p_instance'] = p_instance
        meta['page_id'] = 1

        form_vars = self._get_reload_request_formdata({
            'p_instance': p_instance,
            'x01': self._get_input_value(response, 'apexir_WORKSHEET_ID'),
            'x02': self._get_input_value(response, 'apexir_REPORT_ID'),
            'x03': 'COUNTRY_NAME',
            'x04': 'N',
            'p_widget_action': 'BREAK_TOGGLE',
        })

        yield FormRequest(self.pager_backend_url,
                          method='POST',
                          headers=header_vars,
                          formdata=form_vars,
                          callback=self._parse_page_results,
                          meta=meta)

    def _parse_iframe(self, response):
        """
        Scrape the active foreign principal link out of iframe

        :param response: scrapy response object
        """
        url = Selector(response).xpath("//font[text()='Active Foreign Principals']/../../a/@href").extract_first()
        yield Request(response.urljoin(url), self._toggle_country_column)
        self.logger.debug("Found active foreign principal url %s", url)

    def parse(self, response):
        """
        Scrape the iframe link out of initial page.

        :param response: scrapy response object
        """
        url = response.xpath('//iframe/@src').extract_first()
        yield Request(response.urljoin(url), self._parse_iframe)
        self.logger.debug("Found iframe url %s", url)
