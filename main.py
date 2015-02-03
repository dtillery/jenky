# -*- coding: utf-8 -*-
import argparse
import sys

from jenkins import Jenkins
from workflow import Workflow, ICON_WARNING, PasswordNotFound

from jenky.menus import available_menus, settings_menus
from jenky.menus.initial import InitialMenu
from jenky.menus.settings import SettingsMenu

log = None


def jenky_configured(wf):
    username = wf.settings.get("jenkins_username", None)
    hostname = wf.settings.get("jenkins_hostname", None)
    try:
        api_key = wf.get_password("jenkins_api_key")
    except PasswordNotFound:
        api_key = None
    log.debug("Username is %s" % username)
    log.debug("API Key %s" % (api_key and "exists" or "does not exist"))
    log.debug("Hostname is %s" % hostname)
    return username and hostname and api_key


def get_menu(query, wf):
    menu = None
    if not jenky_configured(wf):
        for m in settings_menus:
            if m.query_match.match(query):
                menu = m(wf, query)
                break
        if not menu:
            menu = InitialMenu(wf, query)
    else:
        pass
    return menu


def main(wf):
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default="")
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