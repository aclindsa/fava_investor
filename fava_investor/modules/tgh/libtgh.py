#!/bin/env python3

from fava_investor.common.libinvestor import val, build_table_footer
from beancount.core.number import Decimal, D
from beancount.core.inventory import Inventory
import collections
import locale


def get_tables(accapi, options):
    retrow_types, to_sell = find_harvestable_lots(accapi, options)
    harvestable_table = retrow_types, to_sell
    by_commodity = harvestable_by_commodity(*harvestable_table)
    summary = summarize_tgh(harvestable_table, by_commodity)
    return harvestable_table, summary, by_commodity


def split_column(cols, col_name, ticker_label='ticker'):
    retval = []
    for i in cols:
        if i[0] == col_name:
            retval.append((col_name, Decimal))
            retval.append((ticker_label, str))
        else:
            retval.append(i)
    return retval


def split_currency(value):
    units = value.get_only_position().units
    return units.number, units.currency


def find_harvestable_lots(accapi, options):
    """Find tax gain harvestable lots.
    - This is intended for the US, but may be adaptable to other countries.
    - This assumes SpecID (Specific Identification of Shares) is the method used for these accounts
    """

    sql = """
    SELECT {account_field} as account,
        units(sum(position)) as units,
        cost_date as acquisition_date,
        value(sum(position)) as market_value,
        cost(sum(position)) as basis
      WHERE account_sortkey(account) ~ "^[01]" AND
        account ~ '{accounts_pattern}'
      GROUP BY {account_field}, cost_date, currency, cost_currency, cost_number, account_sortkey(account)
      ORDER BY account_sortkey(account), currency, cost_date
    """.format(account_field=options.get('account_field', 'LEAF(account)'),
               accounts_pattern=options.get('accounts_pattern', ''))
    rtypes, rrows = accapi.query_func(sql)
    if not rtypes:
        return [], {}

    # Since we GROUP BY cost_date, currency, cost_currency, cost_number, we never expect any of the
    # inventories we get to have more than a single position. Thus, we can and should use
    # get_only_position() below. We do this grouping because we are interested in seeing every lot (price,
    # date) seperately, that can be sold to generate a TGH

    gain_threshold = options.get('gain_threshold', 1)

    # our output table is slightly different from our query table:
    retrow_types = rtypes[:-1] + [('gain', Decimal), ('pct_gain', Decimal)]
    retrow_types = split_column(retrow_types, 'units')
    retrow_types = split_column(retrow_types, 'market_value', ticker_label='currency')

    # rtypes:
    # [('account', <class 'str'>),
    #  ('units', <class 'beancount.core.inventory.Inventory'>),
    #  ('acquisition_date', <class 'datetime.date'>),
    #  ('market_value', <class 'beancount.core.inventory.Inventory'>),
    #  ('basis', <class 'beancount.core.inventory.Inventory'>)]

    RetRow = collections.namedtuple('RetRow', [i[0] for i in retrow_types])

    # build our output table: calculate gains
    to_sell = []

    for row in rrows:
        if row.market_value.get_only_position() and \
                (val(row.market_value) - val(row.basis) > gain_threshold):
            gain = D(val(row.market_value) - val(row.basis))
            pct = D(gain * D(100.0) / val(row.basis))

            to_sell.append(RetRow(row.account, *split_currency(row.units), row.acquisition_date,
                                  *split_currency(row.market_value), gain, pct))

    return retrow_types, to_sell


def harvestable_by_commodity(rtype, rrows):
    """Group input by sum(commodity)
    """

    retrow_types = [('currency', str), ('total_gain', Decimal), ('market_value', Decimal)]
    RetRow = collections.namedtuple('RetRow', [i[0] for i in retrow_types])

    gains = collections.defaultdict(Decimal)
    market_value = collections.defaultdict(Decimal)
    for row in rrows:
        gains[row.ticker] += row.gain
        market_value[row.ticker] += row.market_value

    by_commodity = []
    for ticker in gains:
        by_commodity.append(RetRow(ticker, gains[ticker], market_value[ticker]))

    return retrow_types, by_commodity


def summarize_tgh(harvestable_table, by_commodity):
    # Summary

    locale.setlocale(locale.LC_ALL, '')

    to_sell = harvestable_table[1]
    summary = {}
    summary["Total harvestable gain"] = sum(i.gain for i in to_sell)
    summary["Total sale value required"] = sum(i.market_value for i in to_sell)
    summary["Commmodities with a gain"] = len(by_commodity[1])
    summary["Number of lots to sell"] = len(to_sell)
    unique_txns = set((r.account, r.ticker) for r in to_sell)
    summary["Total unique transactions"] = len(unique_txns)
    summary = {k: '{:n}'.format(int(v)) for k, v in summary.items()}
    return summary
