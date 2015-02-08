# -*- coding: utf-8 -*-
import re

from jenkins import Jenkins
from workflow import ICON_INFO
from workflow.background import run_in_background, is_running

from jenky import QUERY_DELIMITER
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
                "autocomplete": "%s %s Build %s " % (self.job_name, QUERY_DELIMITER, QUERY_DELIMITER)
            }
        ]

    def __init__(self, wf, query):
        super(InitialBuildMenu, self).__init__(wf, query)
        self.job_name = self.query


class BuildJobMenu(BaseMenu):

    query_match = re.compile("^.* %s Build %s\\s?$" % (QUERY_DELIMITER, QUERY_DELIMITER))

    @property
    def items(self):
        return [
            {
                "title": "Build %s" % self.job_name,
                "subtitle": "Start a job build using the parameters you've chosen and any other defaults.",
                "valid": True,
                "arg": "Let's build %s!" % self.job_name

            }
        ]

    def __init__(self, wf, query):
        super(BuildJobMenu, self).__init__(wf, query)
        query_parts = self.query.split(" %s " % QUERY_DELIMITER)
        self.job_name = query_parts[0]
        # TODO: for filtering items, should modify query to remove build-info and filter on remaining

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


class ParamMenu(BaseMenu):
    pass