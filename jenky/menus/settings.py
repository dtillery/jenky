# -*- coding: utf-8 -*-
import re

from jenky import QUERY_DELIMITER
from jenky.menus.base import BaseMenu

class SettingsMenu(BaseMenu):

    query_match = re.compile("^s$")

    @property
    def items(self):
        return [
            {
                "title": "Welcome to the Settings menu.",
                "subtitle": "Configure your Jenkins username, api key and hostname via the options below.",
                "valid": False
            },
            {
                "title": "Set Username",
                "subtitle": "Set your Jenkins username to be used for authentication.",
                "valid": False,
                "autocomplete": u"Username %s " % QUERY_DELIMITER
            },
            {
                "title": "Set API Key",
                "subtitle": "Set your Jenkins API key securely in the system Keychain.",
                "valid": False,
                "autocomplete": u"API Key %s " % QUERY_DELIMITER
            },
            {
                "title": "Set Hostname",
                "subtitle": "Set your Jenkins instances' base hostname (e.g. 'https://my-jenkins.awesome.com').",
                "valid": False,
                "autocomplete": u"Hostname %s " % QUERY_DELIMITER
            }
        ]

class UsernameMenu(BaseMenu):

    query_match = re.compile(u"^Username %s " % QUERY_DELIMITER)

    @property
    def items(self):
        return [
            {
                "title": "Set your Jenkins username.",
                "subtitle": "Whatever you normally use to sign into your Jenkins instance.",
                "valid": True,
                "arg": self.output
            }
        ]

    @property
    def output(self):
        username = self.query.split(QUERY_DELIMITER)[1].strip()
        return "username:%s" % username


class APIKeyMenu(BaseMenu):

    query_match = re.compile(u"^API Key %s " % QUERY_DELIMITER)

    @property
    def items(self):
        return [
            {
                "title": "Set your Jenkins API Key.",
                "subtitle": "You can find this on your personal 'Configure' page in Jenkins (click your name in the top right).",
                "valid": True,
                "arg": self.output
            }
        ]

    @property
    def output(self):
        api_key = self.query.split(QUERY_DELIMITER)[1].strip()
        return "api_key:%s" % api_key


class HostnameMenu(BaseMenu):

    query_match = re.compile(u"^Hostname %s " % QUERY_DELIMITER)

    @property
    def items(self):
        return [
            {
                "title": "Set your Jenkins hostname.",
                "subtitle": "The URL of your jenkins instance, e.g. 'https://my-jenkins.awesome.com' (no trailing slash).",
                "valid": True,
                "arg": self.output
            }
        ]

    @property
    def output(self):
        hostname = self.query.split(QUERY_DELIMITER)[1].strip()
        return "hostname:%s" % hostname