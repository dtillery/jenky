# -*- coding: utf-8 -*-
import argparse
import sys

from workflow import Workflow, ICON_WARNING, PasswordNotFound

from jenky.menus import settings_menus
from jenky.menus.settings import SettingsMenu

log = None

def get_menu(query, wf):
    menu = None
    for m in settings_menus:
        if m.query_match.match(query):
            menu = m(wf, query)
            break
    return menu

def main(wf):
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default="")
    args = parser.parse_args(wf.args)

    query = args.query

    menu = get_menu(query, wf)
    if menu:
        menu.set_menu()
        return 0

    wf.add_item("Could not get approriate menu.",
                "This shouldn't happen, please report your query to the jenky developer",
                valid=False,
                icon=ICON_WARNING)
    wf.send_feedback()
    return 0

if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
