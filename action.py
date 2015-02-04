# -*- coding: utf-8 -*-
import argparse
import sys

from workflow import Workflow, ICON_WARNING, PasswordNotFound

log = None

def main(wf):
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default="")
    args = parser.parse_args(wf.args)

    query = args.query

    # Settings
    log.debug(query)
    if query.startswith("jenky_setting:"):
        query = query.replace("jenky_setting:", "")
        if query.startswith("username:"):
            log.debug("Saving username: %s" % query)
            query = query.replace("username:", "")
            wf.settings["jenkins_username"] = query
            print "Username set as \"%s\"." % query
            return 0
        elif query.startswith("api_key:"):
            log.debug("Saving API Key...")
            query = query.replace("api_key:", "")
            wf.save_password("jenkins_api_key", query)
            print "API Key has been set."
            return 0
        elif query.startswith("hostname:"):
            log.debug("Saving hostname: %s" % query)
            query = query.replace("hostname:", "")
            wf.settings["jenkins_hostname"] = query
            print "Hostname set as \"%s\"." % query
            return 0
    # Jenky Actions
    elif query.startswith("jenky_action:"):
        query = query.replace("jenky_action:", "")
        # Clear out the Job cache
        if query.startswith("clear_job_cache"):
            log.debug("Clearing out Job cache...")
            wf.clear_cache(lambda f: f.startswith("jobs"))
            print "The job cache has been cleared."
            return 0
    return 0


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
