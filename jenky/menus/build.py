# -*- coding: utf-8 -*-
import re

from jenkins import Jenkins

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
        self.username = wf.settings.get("jenkins_username", None)
        self.hostname = wf.settings.get("jenkins_hostname", None)
        try:
            self.api_key = wf.get_password("jenkins_api_key")
        except PasswordNotFound:
            self.api_key = None
        # TODO: backgroud updates


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
        # for filtering items, should modify query to remove build-info and filter on remaining

class ParamMenu(BaseMenu):
    pass