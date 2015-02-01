# -*- coding: utf-8 -*-

import argparse
import sys

from jenkins import Jenkins
from workflow import Workflow, ICON_WARNING, PasswordNotFound

from jenky.menus import settings, initial

log = None

def jenky_configured(wf):
    username = wf.settings.get("jenkins_username", None)
    hostname = wf.settings.get("jenkins_hostname", None)
    try:
        api_key = wf.get_password("jenkins_api_key")
    except PasswordNotFound:
        api_key = None
    return username and hostname and api_key


def get_menu(query, wf):
    menu = None
    if not jenky_configured(wf):
        menu = initial.InitialMenu(wf)
    if query == "s":
        menu = settings.SettingsMenu(wf)
    return menu


def main(wf):
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default=None)
    args = parser.parse_args(wf.args)

    # get Appropriate menu to display
    menu = get_menu(args.query, wf)
    if menu:
        menu.set_menu()
        return 0

    # No menu found, return error.  Should never happen.
    # for some reason I couldn't put this in an if block...
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