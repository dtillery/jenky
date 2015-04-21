# -*- coding: utf-8 -*-
import json
import re

from jenkins import Jenkins
from six.moves.urllib.request import Request
from workflow import ICON_INFO, ICON_ERROR, ICON_WARNING
from workflow.background import run_in_background, is_running

from jenky import QUERY_DELIMITER, SUBQUERY_DELIMITER
from jenky.menus.base import BaseMenu

PARAM_DEF_MAP = {
    "BooleanParameterDefinition": "Boolean Parameter",
    "StringParameterDefinition": "String Parameter",
    "ChoiceParameterDefinition": "Choice Parameter",
    "PasswordParameterDefinition": "Password Parameter"
}

def parse_inline_params(params_string):
    if not params_string:
        return {}
    params = {}
    params_list = params_string.split(SUBQUERY_DELIMITER)
    if params_list.pop(0) != "params":
        log.debug("Params String messed up: %s" % params_string)
        return {}
    if len(params_list) % 2 != 0:
        log.debug("Params list length not even: %s" % params_list)
        return {}
    return {params_list[i]: params_list[i+1] for i in range(0, len(params_list), 2)}


class InitialBuildMenu(BaseMenu):

    query_match = re.compile("^(?!\s*$).+")

    @property
    def items(self):
        return [
            {
                "title": "Build %s job." % self.job_name,
                "subtitle": "Enter the build menu to set parameters and start a build.",
                "valid": False,
                "autocomplete": "%(name)s %(del)s Build %(del)s " % {"name":self.job_name, "del":QUERY_DELIMITER}
            },
            {
                "title": "Build History.",
                "subtitle": "View recent builds and re-run them.",
                "valid": False,
                "autocomplete": "%(name)s %(del)s Build History %(del)s " % {"name":self.job_name, "del":QUERY_DELIMITER}
            }
        ]

    def __init__(self, wf, query):
        super(InitialBuildMenu, self).__init__(wf, query)
        self.job_name = self.query


class BuildJobMenu(BaseMenu):

    query_match = re.compile("^.* %s Build %s\\s*.*$" % (QUERY_DELIMITER, QUERY_DELIMITER))

    @property
    def items(self):
        items = []
        if not self.searching_for_param:
            items.append({
                "title": "Build %s" % self.job_name,
                "subtitle": "Start a job build using the parameters you've set (and defaults otherwise).",
                "valid": True,
                "arg": "jenky_action:build:%s%s%s" % (self.job_name, SUBQUERY_DELIMITER, self.existing_query_params)

            })
        if self.parameters:
            for param in self.parameters:
                name = param.get("name", None)
                t = param.get("type", "No type")
                desc = param.get("description", "No description available.")
                if name in self.chosen_params:
                    val = self.chosen_params.get(name)
                    if val.startswith("jenkybool"):
                        val = val == "jenkybooltrue"
                else:
                    val = param.get("defaultParameterValue", {}).get("value", "No default")
                item = {
                    "title": "%s (%s)" % (name, val),
                    "subtitle": "%s: %s" % (PARAM_DEF_MAP.get(t), desc),
                    "valid": False,
                    "autocomplete": self.build_param_menu_string(name)
                }
                items.append(item)
        return items


    def __init__(self, wf, query):
        super(BuildJobMenu, self).__init__(wf, query)
        self.query_parts = [q.strip() for q in self.query.split("%s" % QUERY_DELIMITER)]
        self.job_name = self.query_parts[0]
        self.existing_query_params = SUBQUERY_DELIMITER in self.query_parts[1] and self.query_parts[1]
        self.chosen_params = parse_inline_params(self.existing_query_params)

        # check job param freshness, 1 day
        if not self.wf.cached_data_fresh("%s_params" % self.job_name, 86400):
            # run background upate for params
            self.log.debug("Starting background update for %s params" % self.job_name)
            run_in_background("update_job_params_%s" % self.job_name,
                              ['/usr/bin/python',
                              self.wf.workflowfile("background_update.py"),
                                                   "--params", self.job_name])

        # add notification if running
        if is_running("update_job_params_%s" % self.job_name):
            self.wf.add_item("Updating parameter options...",
                             "This should only take a minute. You can continue using the currently cached data",
                             icon=ICON_INFO,
                             valid=False,
                             autocomplete=self.query)

        self.parameters = self.wf.cached_data("%s_params" % self.job_name, max_age=0)
        self.searching_for_param = False
        if self.query_parts[-1] and not self.query_parts[-1].startswith("Build"):
            self.searching_for_param = True
            self.parameters = self.wf.filter(self.query_parts[-1], self.parameters, key=self.search_key_for_param, min_score=20)

    def search_key_for_param(self, param):
        return param.get("name", "")

    def build_param_menu_string(self, param_name):
        s = "%(jn)s %(del)s "
        if self.existing_query_params:
            s += "%(qp)s %(del)s "
        s += "Set Param %(del)s %(pn)s %(del)s "
        return s % {
            "jn": self.job_name,
            "del": QUERY_DELIMITER,
            "qp": self.existing_query_params,
            "pn": param_name
        }


class ParamMenu(BaseMenu):

    query_match = re.compile("^.* %s Set Param %s\\s*.*$" % (QUERY_DELIMITER, QUERY_DELIMITER))

    @property
    def items(self):
        val_to_use = self.chosen_params.get(self.param_name) or self.param_info.get("defaultParameterValue", {}).get("value", "No Default")
        if self.param_type == "StringParameterDefinition":
            items = [
                {
                    "title": "Type in your value for %s (%s)." % (self.param_name, val_to_use),
                    "subtitle": self.param_info.get("description", "No description available."),
                    "valid": False,
                    "autocomplete": self.build_param_set_string(self.query_parts[-1] or val_to_use)
                }
            ]
        elif self.param_type == "ChoiceParameterDefinition":
            items = [
                {
                    "title": "Choose a value for %s (%s)." % (self.param_name, val_to_use),
                    "subtitle": self.param_info.get("description", "No description available."),
                    "valid": False,
                    "autocomplete": self.build_param_set_string(val_to_use)
                }
            ]
            for choice in self.param_info.get("choices", []):
                items.append({
                        "title": choice,
                        "valid": False,
                        "autocomplete": self.build_param_set_string(choice)
                    })
        elif self.param_type == "BooleanParameterDefinition":
            items = [
                {
                    "title": "Choose a boolean for %s (%s)." % (self.param_name, val_to_use),
                    "subtitle": self.param_info.get("description", "No description available."),
                    "valid": False,
                    "autocomplete": self.build_param_set_string(val_to_use)

                },
                {
                    "title": "True",
                    "valid": False,
                    "autocomplete": self.build_param_set_string("jenkybooltrue")
                },
                {
                    "title": "False",
                    "valid": False,
                    "autocomplete": self.build_param_set_string("jenkyboolfalse")
                },
            ]
        elif self.param_type == "PasswordParameterDefinition":
            items = [
                {
                    "title": "Type in your password value for %s." % self.param_name,
                    "subtitle": self.param_info.get("description", "No description available."),
                    "valid": False,
                    "autocomplete": self.build_param_set_string(self.query_parts[-1] or val_to_use)
                }
            ]
        else:
            items = [
                {
                    "title": "Unknown paramter type: %s" % self.param_type,
                    "subtitle": "Please report this type and use case to the developer.",
                    "valid": False,
                    "autocomplete": self.query,
                    "icon": ICON_ERROR
                }
            ]
        items.append({
                "title": "Cancel parameter set.",
                "subtitle": "Return to the main build menu.",
                "valid": False,
                "autocomplete": self.query,
                "icon": ICON_WARNING
            })
        return items


    def __init__(self, wf, query):
        super(ParamMenu, self).__init__(wf, query)
        self.query_parts = [q.strip() for q in self.query.split("%s" % QUERY_DELIMITER)]
        self.job_name = self.query_parts[0]
        self.existing_query_params = SUBQUERY_DELIMITER in self.query_parts[1] and self.query_parts[1]
        self.chosen_params = parse_inline_params(self.existing_query_params)
        self.param_name = self.query_parts[-2]

        parameters = self.wf.cached_data("%s_params" % self.job_name, max_age=0)
        for param in parameters:
            if param.get("name", "") == self.param_name:
                self.param_info = param
                break
        self.param_type = self.param_info.get("type")

    def build_param_set_string(self, choice):
        if not self.existing_query_params:
            self.existing_query_params = "params"
        new_params_string = "%(ex)s%(del)s%(name)s%(del)s%(choice)s" % {
            "ex": self.existing_query_params,
            "del": SUBQUERY_DELIMITER,
            "name": self.param_name,
            "choice": choice
        }
        s = "%(jn)s %(del)s "
        s += "%(nps)s %(del)s "
        s += "Build %(del)s "
        return s % {
            "jn": self.job_name,
            "del": QUERY_DELIMITER,
            "nps": new_params_string
        }


class BuildHistoryMenu(BaseMenu):

    query_match = re.compile("^.* %s Build History %s\\s*.*$" % (QUERY_DELIMITER, QUERY_DELIMITER))

    @property
    def items(self):
        items = []
        for build in self.recent_build_list:
            self.log.debug(self.build_rerun_string(build.get("parameters", {})))
            sub = ", ".join(["%s:%s" % (p.get("name"), p.get("value")) for p in build.get("parameters", {})])
            items.append({
                "title": build.get("name", "No Build Name").replace("%s " % self.job_name, ""),
                "subtitle": sub,
                "valid": False,
                "autocomplete": self.build_rerun_string(build.get("parameters", {}))
            })
        if not items:
            items.append({
                "title": "No recent builds that match \"%s\"." % self.query,
                "valid": False
            })
        return items

    def __init__(self, wf, query):
        super(BuildHistoryMenu, self).__init__(wf, query)
        self.query_parts = [q.strip() for q in self.query.split("%s" % QUERY_DELIMITER)]
        self.job_name = self.query_parts[0]
        self.username = wf.settings.get("jenkins_username", None)
        self.hostname = wf.settings.get("jenkins_hostname", None)
        try:
            self.api_key = wf.get_password("jenkins_api_key")
        except PasswordNotFound:
            self.api_key = None

        # would love to display "in progress" message while working...
        # if self.wf.cached_data_age("build_history_%s" % self.job_name) == 0:
        #     self.wf.add_item("Retrieving Build History...",
        #                      "This should only take a minute.",
        #                      icon=ICON_INFO,
        #                      valid=False,
        #                      autocomplete=self.query)
        #     self.wf.send_feedback()

        # cache for 2 minutes
        self.recent_build_list = self.wf.cached_data("build_history_%s" % self.job_name, self.get_recent_builds, 120)
        if self.query_parts[-1] and not self.query_parts[-1].startswith("Recent"):
            self.recent_build_list = self.wf.filter(self.query_parts[-1], self.recent_build_list, key=self.search_key_for_build)

    def get_recent_builds(self):
        j = Jenkins(self.hostname, self.username, self.api_key)
        r = Request(j.server + "job/%s/api/json?tree=builds[url,fullDisplayName,actions[parameters[name,value]]]" % self.job_name)
        response = json.loads(j.jenkins_open(r))
        builds = response.get("builds", [])
        final = []
        for b in builds:
            info = {}
            for d in b.get("actions", []):
                if "parameters" in d.keys():
                    info["parameters"] = d.get("parameters", [])
                    break
            info["url"] = b.get("url", "")
            info["name"] = b.get("fullDisplayName", "")
            final.append(info)
        return final

    def search_key_for_build(self, build):
        return build.get("name", "")

    def build_rerun_string(self, params):
        param_string = ""
        s = "%(jn)s %(del)s "
        s += "params"
        for p in params:
            n = p.get("name")
            v = p.get("value")
            if v:
                if v is True or v is False:
                    v = v and "jenkybooltrue" or "jenkyboolfalse"
                s += "%s%s%s%s" % (SUBQUERY_DELIMITER, n, SUBQUERY_DELIMITER, v)
        s += " %(del)s Build %(del)s "

        return s % {
            "jn": self.job_name,
            "del": QUERY_DELIMITER,
            "sdel": SUBQUERY_DELIMITER
        }
