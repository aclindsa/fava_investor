#!/usr/bin/env python3

import beancountinvestorapi as api
import functools
import datetime
from beancount.utils import test_utils
import libtgh
# python3 -m unittest discover . to run


class TestScriptCheck(test_utils.TestCase):
    def setUp(self):
        self.options = {'accounts_pattern': "Assets:Investments:Taxable",
                        'gain_threshold': 10,
                        }

    @test_utils.docfile
    def test_no_relevant_accounts(self, f):
        """
        2010-01-01 open Assets:Investments:Brokerage
        2010-01-01 open Assets:Bank

        2010-02-01 * "Buy stock"
         Assets:Investments:Brokerage 1 BNCT {{100 USD}}
         Assets:Bank

        2011-05-15 price BNCT 200 USD
        """
        accapi = api.AccAPI(f, {})

        retrow_types, to_sell = libtgh.find_harvestable_lots(accapi, self.options)

        self.assertEqual(0, len(to_sell))

    @test_utils.docfile
    def test_harvestable_basic(self, f):
        """
        2010-01-01 open Assets:Investments:Taxable:Brokerage
        2010-01-01 open Assets:Bank

        2010-02-01 * "Buy stock"
         Assets:Investments:Taxable:Brokerage 1 BNCT {{100 USD}}
         Assets:Bank

        2011-05-15 price BNCT 200 USD
        """
        accapi = api.AccAPI(f, {})

        retrow_types, to_sell = libtgh.find_harvestable_lots(accapi, self.options)

        self.assertEqual(1, len(to_sell))

    @test_utils.docfile
    def test_harvestable_below_threshold(self, f):
        """
        2010-01-01 open Assets:Investments:Taxable:Brokerage
        2010-01-01 open Assets:Bank

        2010-02-01 * "Buy stock"
         Assets:Investments:Taxable:Brokerage 1 BNCT {{100 USD}}
         Assets:Bank

        2011-05-15 price BNCT 109 USD
        """
        accapi = api.AccAPI(f, {})

        retrow_types, to_sell = libtgh.find_harvestable_lots(accapi, self.options)

        self.assertEqual(0, len(to_sell))

    @test_utils.docfile
    def test_harvestable_no_losses(self, f):
        """
        2010-01-01 open Assets:Investments:Taxable:Brokerage
        2010-01-01 open Assets:Bank

        2010-02-01 * "Buy stock"
         Assets:Investments:Taxable:Brokerage 1 BNCT {{200 USD}}
         Assets:Bank

        2011-05-15 price BNCT 100 USD
        """
        accapi = api.AccAPI(f, {})

        retrow_types, to_sell = libtgh.find_harvestable_lots(accapi, self.options)

        self.assertEqual(0, len(to_sell))
