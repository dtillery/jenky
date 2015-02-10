# -*- coding: utf-8 -*-
import argparse
import sys

from jenkins import Jenkins, NotFoundException, JenkinsException
from workflow import Workflow, ICON_WARNING, PasswordNotFound

from jenky import SUBQUERY_DELIMITER

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


def parse_params_list(params_list):
    if not params_list:
        return {}
    params = {}
    if params_list.pop(0) != "params":
        log.debug("Params String messed up: %s" % params_list)
        return {}
    if len(params_list) % 2 != 0:
        log.debug("Params list length not even: %s" % params_list)
        return {}
    return {params_list[i]: params_list[i+1] for i in range(0, len(params_list), 2)}


def build(wf, build_string):
    build_string_parts = build_string.split(SUBQUERY_DELIMITER)
    job_name = build_string_parts.pop(0)
    passed_params = parse_params_list(build_string_parts)
    job_parameters = wf.cached_data("%s_params" % job_name, max_age=0)
    if not job_parameters:
        print "Job Failed: could not get any existing job parameters for %s" % job_name
        return
    final_params = {}
    for param in job_parameters:
        name = param.get("name", None)
        chosen_val = passed_params.get(name, None)
        final_val = chosen_val or param.get("defaultParameterValue", {}).get("value", "")
        # translate bools
        if isinstance(final_val, basestring) and final_val.startswith("jenkybool"):
            final_val = final_val == "jenkybooltrue"
        final_params[name] = final_val

    username, api_key, hostname = get_jenkins_credentials(wf)
    j = Jenkins(hostname, username, api_key)
    try:
        o = j.build_job(job_name, parameters=final_params)
    except NotFoundException:
        print "Build Failed: \"%s\" job could not be found." % job_name
    except Exception as e:
        print "Build Failed: Unknown Error - %s" % e
    except JenkinsException as e:
        print "Build Failed: %s" % e
    else:
        print "Build Success: %s build queued." % job_name
    return 0


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
        elif query.startswith("build:"):
            query = query.replace("build:", "")
            log.debug("Starting a build...")
            build(wf, query)
    return 0


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
