#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# Description: Beancount Tax Gain Harvester

import libtgh
import beancountinvestorapi as api
import argh
import argcomplete
import tabulate


def tgh(beancount_file,
        accounts_pattern='',
        gain_threshold=10,
        brief=False
        ):
    '''Finds opportunities for tax gain harvesting in a beancount file'''
    argsmap = locals()
    accapi = api.AccAPI(beancount_file, argsmap)

    config = {'accounts_pattern': accounts_pattern, 'gain_threshold': gain_threshold}
    harvestable_table, summary, by_commodity = libtgh.get_tables(accapi, config)
    to_sell_types, to_sell = harvestable_table

    def pretty_print(title, types, rows):
        if title:
            print(title)
        headers = [l[0] for l in types]
        if rows:
            print(tabulate.tabulate(rows, headers=headers))
        else:
            print('(empty table)')
        print()

    for k, v in summary.items():
        print("{:30}: {:>}".format(k, v))
    print()
    pretty_print("By commodity", *by_commodity)

    if not brief:
        pretty_print("Lot detail", *harvestable_table)

        print("See fava plugin for better formatted and sortable output.")

# -----------------------------------------------------------------------------


def main():
    parser = argh.ArghParser(description="Beancount Tax Gain Harvester")
    argh.set_default_command(parser, tgh)
    argh.completion.autocomplete(parser)
    parser.dispatch()


if __name__ == '__main__':
    main()
