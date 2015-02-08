# -*- coding: utf-8 -*-
import re

from jenkins import Jenkins
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
                "arg": "Let's build %s!" % self.job_name

            })
        if self.parameters:
            for param in self.parameters:
                name = param.get("name", None)
                t = param.get("type", "No type")
                desc = param.get("description", "No description available.")
                default = param.get("defaultParameterValue", {}).get("value", None)
                if default is None:
                    default = "No default"
                item = {
                    "title": "%s (%s)" % (name, default),
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
        if self.param_type == "StringParameterDefinition":
            items = [
                {
                    "title": "Type in your value for %s." % self.param_name,
                    "subtitle": self.param_info.get("description", "No description available."),
                    "valid": False,
                    "autocomplete": self.build_param_set_string(self.query_parts[-1])
                }
            ]
        elif self.param_type == "ChoiceParameterDefinition":
            items = [
                {
                    "title": "Choose a value for %s." % self.param_name,
                    "subtitle": self.param_info.get("description", "No description available."),
                    "valid": False,
                    "autocomplete": self.query
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
                    "title": "Choose a boolean for %s." % self.param_name,
                    "subtitle": self.param_info.get("description", "No description available."),
                    "valid": False,
                    "autocomplete": self.query

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
                    "autocomplete": self.build_param_set_string(self.query_parts[-1])
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