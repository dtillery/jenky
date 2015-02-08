# -*- coding: utf-8 -*-
import argparse
import sys

from jenkins import Jenkins
from workflow import Workflow, ICON_WARNING, PasswordNotFound

from jenky.menus import settings_menus
from jenky.menus.settings import SettingsMenu

log = None


def get_jenkins_credentials(wf):
    username = wf.settings.get("jenkins_username", None)
    hostname = wf.settings.get("jenkins_hostname", None)
    try:
        api_key = wf.get_password("jenkins_api_key")
    except PasswordNotFound:
        api_key = None
    if not username and hostname and api_key:
        log.error("Credentials not all found. Check your username, api key and hostname settings.")
    log.debug("Username: %s" % username)
    log.debug("Hostname: %s" % hostname)
    return username, api_key, hostname


def get_job_params(job, hostname, username, api_key):
    j = Jenkins(hostname, username, api_key)
    log.debug("Retrieving Jenkins info for %s" % job)
    job_info = j.get_job_info(job)
    for d in job_info.get("actions", []):
        if isinstance(d, dict) and "parameterDefinitions" in d.keys():
            return d.get("parameterDefinitions", [])


def main(wf):
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", dest="update_job_params", action="store_true")
    parser.add_argument("query", nargs="?", default="")
    args = parser.parse_args(wf.args)

    log.debug("Running a background update for job %s" % args.query)
    if args.update_job_params:
        job = args.query
        log.debug("Updating job parameters for %s" % job)
        username, api_key, hostname = get_jenkins_credentials(wf)
        def param_wrapper():
            return get_job_params(job, hostname, username, api_key)
        success = wf.cached_data("%s_params" % job, param_wrapper, max_age=86400)

    if not success:
        log.error("Background update not successful.")
        return 1

    log.debug("Background update successful")
    return 0

if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
