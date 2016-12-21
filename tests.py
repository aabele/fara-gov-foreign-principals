# -*- coding: utf8 -*-
"""
ForeignPrincipalSpider unittests
"""

from __future__ import unicode_literals

import os
import unittest

from fara.spiders.fara import ForeignPrincipalSpider


class FakeResponse(object):
    """
    Simplified mock of `scrapy.http.Response` object
    """

    status = 200
    body = bytes()

    def __init__(self, file_name, url):
        self.url = url

        base_dir = os.path.dirname(os.path.realpath(__file__))

        f = open(os.path.join(base_dir, 'responses', file_name))
        self.body = bytes(f.read(), encoding='utf8')
        f.close()

        self.text = str(self.body)


class ForeignPrincipalSpiderTestCase(unittest.TestCase):
    """
    Testing `fara.spiders.fara.ForeignPrincipalSpider` methods that return actual value.

    However with this approach i'm unable to test methods that contains `yield`. Most likely they could be tested by
    checking pipeline or so.
    """

    xhr_backend_url = 'https://efile.fara.gov/pls/apex/wwv_flow.show'

    fake_principal_index_page = FakeResponse('principal_index_page.html', xhr_backend_url)
    fake_last_principal_index_page = FakeResponse('last_principal_index_page.html', xhr_backend_url)
    fake_single_row_principal_index_page = FakeResponse('single_row_principal_index_page.html', xhr_backend_url)
    fake_initial_principal_index_page = FakeResponse(
        'initial_principal_index_page.html',
        'https://efile.fara.gov/pls/apex/f?p=171:130:0::NO:RP,130:P130_DATERANGE:N'
    )

    def setUp(self):
        super(ForeignPrincipalSpiderTestCase, self).setUp()
        self.spider = ForeignPrincipalSpider()

    def test_to_datetime(self):
        """ Should turn string into valid datetime """
        month = 12
        day = 10
        year = 1997
        response = self.spider._to_datetime('%s/%s/%s' % (month, day, year))
        self.assertEqual(response.year, year)
        self.assertEqual(response.day, day)
        self.assertEqual(response.month, month)
        self.assertEqual(response.minute, 0)
        self.assertEqual(response.second, 0)
        self.assertEqual(response.hour, 0)

    def test_reload_request_headers(self):
        """ Should allow to override any header """
        method = self.spider._get_reload_request_headers
        default = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'efile.fara.gov',
            'Origin': 'https://efile.fara.gov',
        }
        response = method()
        self.assertEqual(response, default)

        new_host = 'www.microsoft.com'
        response = method({
            'Host': new_host,
        })
        default['Host'] = new_host
        self.assertEqual(response, default)

    def test_reload_request_formdata(self):
        """ Should allow to override any form field """
        method = self.spider._get_reload_request_formdata
        default = {
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
        }
        response = method()
        self.assertEqual(response, default)

        new_p_instance = 'xxx'
        response = method({
            'p_instance': new_p_instance,
        })
        default['p_instance'] = new_p_instance
        self.assertEqual(response, default)

    def test_get_pages_total(self):
        """ Should calculate valid additional page count """
        additional_pages = self.spider._get_pages_total(self.fake_principal_index_page)
        self.assertEqual(34, additional_pages)

    def test_has_next_page(self):
        """ Should tell if there are next result page """
        self.assertTrue(self.spider._has_next_page(self.fake_principal_index_page))
        self.assertFalse(self.spider._has_next_page(self.fake_last_principal_index_page))

    def test_get_input_value(self):
        """ Should return specified form element value attribute value """
        # Element html
        # <input type="hidden" name="p_instance" value="355896116786" id="pInstance" />
        response = self.spider._get_input_value(self.fake_initial_principal_index_page, 'pInstance')
        self.assertEqual('355896116786', response)

    def test_parse_column(self):
        """ Should return valid row column value """

        # Testing usual column
        # <td  align="left" headers="REG_DATE">10/03/2005</td>
        response = self.spider._parse_column(self.fake_single_row_principal_index_page, 'REG_DATE', test_mode=True)
        self.assertEqual('10/03/2005', response)

        # Testing whitespace trimming
        # <td  align="center" headers="REG_NUMBER">5712      </td>
        response = self.spider._parse_column(self.fake_single_row_principal_index_page, 'REG_NUMBER', test_mode=True)
        self.assertEqual('5712', response)

    def test_get_pager_params(self):
        """ Should generate valid pager params """
        self.assertEqual(self.spider._get_pager_params(1), 'pgR_min_row=16max_rows=15rows_fetched=15')
        self.assertEqual(self.spider._get_pager_params(5), 'pgR_min_row=76max_rows=15rows_fetched=15')

if __name__ == '__main__':
    unittest.main()
