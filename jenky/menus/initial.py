# -*- coding: utf-8 -*-
import re

from jenky.menus.base import BaseMenu

class InitialMenu(BaseMenu):

    query_match = re.compile("^$")

    @property
    def items(self):
        return [
            {
                "title": "Welcome to Jenky!",
                "subtitle": "Start typing the name of a job...",
                "valid": False
            },
            {
                "title": "Go to Settings",
                "subtitle": "You can change your username, API key and hostname here.",
                "valid": True,
                "arg": "jenky-settings"
            },
            {
                "title": "Clear Job Cache",
                "subtitle": "Clear out the local Job cache. Data will be fetched from the server on next launch.",
                "valid": True,
                "arg": "jenky-clear-job-cache"
            }
        ]