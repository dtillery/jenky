# -*- coding: utf-8 -*-
import re

from jenkins import Jenkins
from workflow import ICON_INFO
from workflow.background import run_in_background, is_running

from jenky import QUERY_DELIMITER, SUBQUERY_DELIMITER
from jenky.menus.base import BaseMenu


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
                "subtitle": "Start a job build using the parameters you've chosen and any other defaults.",
                "valid": True,
                "arg": "Let's build %s!" % self.job_name

            })
        if self.parameters:
            for param in self.parameters:
                name = param.get("name", None)
                t = param.get("type", "No type")
                default = param.get("defaultParameterValue", {}).get("value", None)
                if default is None:
                    default = "No default value."
                item = {
                    "title": name,
                    "subtitle": "%s: %s" % (t, default),
                    "valid": False,
                    "autocomplete": self.build_param_menu_string(name)
                }
                items.append(item)
        return items


    def __init__(self, wf, query):
        super(BuildJobMenu, self).__init__(wf, query)
        self.query_parts = [q.strip() for q in self.query.split("%s" % QUERY_DELIMITER)]
        self.job_name = self.query_parts[0]
        self.query_params = SUBQUERY_DELIMITER in self.query_parts[1] and self.query_parts[1]

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
        if self.query_params:
            s += "%(qp)s %(del)s "
        s += "Set Param %(del)s %(pn)s %(del)s "
        return s % {
            "jn": self.job_name,
            "del": QUERY_DELIMITER,
            "qp": self.query_params,
            "pn": param_name
        }


class ParamMenu(BaseMenu):
    pass