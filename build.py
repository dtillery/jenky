# -*- coding: utf-8 -*-
import argparse
import re
import sys

from workflow import Workflow, ICON_ERROR

from jenky.menus import build_menus

log = None


def parse_job_from_url(query):
    # match on Jenkins URLs like ".../jobs/Job_Name/#"
    pattern = re.compile("^.*/job/(.*)/#?$")
    m = pattern.match(query)
    if m:
        try:
            return m.group(1)
        except Exception, e:
            log.debug("Could not parse %s: %s" % (query, e))
            return None
    log.debug("No match for %s" % query)
    return None


def get_menu(query, wf):
    menu = None
    for m in build_menus:
        if m.query_match.match(query):
            menu = m(wf, query)
            break
    return menu


def main(wf):
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default="")
    args = parser.parse_args(wf.args)

    query = args.query
    # job_name = parse_job_from_url(query)
    job_name = args.query

    if not job_name:
        wf.add_item("No job name given.",
                "Please enter a valid job name.",
                valid=False,
                icon=ICON_ERROR)
        wf.send_feedback()
        return 0

    log.debug("Getting menu for %s" % job_name)
    menu = get_menu(query, wf)
    if menu:
        menu.set_menu()
        return 0

    wf.add_item("Could not get approriate menu.",
                "This shouldn't happen, please report your query to the jenky developer",
                valid=False,
                icon=ICON_ERROR)
    wf.send_feedback()
    return 0


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
