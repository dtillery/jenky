# -*- coding: utf-8 -*-
import re

from jenkins import Jenkins

from jenky import QUERY_DELIMITER
from jenky.menus.base import BaseMenu

class JobsMenu(BaseMenu):

    query_match = re.compile("^(?!\s*$).+")

    @property
    def items(self):
        items = []
        for job in self.jobs:
            items.append({
                "title": job.get("name", "Unknown Job Name"),
                "subtitle": job.get("url", ""),
                "valid": True,
                "arg": job.get("url"),
                "uid": job.get("name")
            })
        if not items:
            items.append({
                "title": "No jobs found matching \"%s\"." % self.query,
                "valid": False
            })
        return items


    def __init__(self, wf, query):
        super(JobsMenu, self).__init__(wf, query)
        self.username = wf.settings.get("jenkins_username", None)
        self.hostname = wf.settings.get("jenkins_hostname", None)
        try:
            self.api_key = wf.get_password("jenkins_api_key")
        except PasswordNotFound:
            self.api_key = None

        #TODO: handle settings missing

        self.jobs = wf.cached_data("jobs", self.get_jobs, max_age=0)
        if query:
            self.jobs = wf.filter(query, self.jobs, key=self.search_key_for_job, min_score=20)

    def get_jobs(self):
        j = Jenkins(self.hostname, self.username, self.api_key)
        jobs = j.get_jobs()
        return jobs

    def search_key_for_job(self, job):
        return job.get("name", "")