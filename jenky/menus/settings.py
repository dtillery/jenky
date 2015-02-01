# -*- coding: utf-8 -*-

from jenky.menus.base import BaseMenu

class SettingsMenu(BaseMenu):

    def __init__(self, wf):
        super(SettingsMenu, self).__init__(wf)

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
                "autocomplete": u"Username %(del)s " % self.str_format
            },
            {
                "title": "Set API Key",
                "subtitle": "Set your Jenkins API key securely in the system Keychain.",
                "valid": False,
                "autocomplete": u"API Key %(del)s " % self.str_format
            },
            {
                "title": "Set Hostname",
                "subtitle": "Set your Jenkins instances' base hostname (e.g. 'https://my-jenkins.awesome.com').",
                "valid": False,
                "autocomplete": u"Hostname %(del)s " % self.str_format
            }
        ]

class UsernameMenu(BaseMenu):

    def __init__(self, wf):
        super(Username, self).__init__(wf)

    @property
    def items(self):
        return [
            {
                "title": "Set your Jenkins username.",
                "subtitle": "Whatever you normally use to sign into your Jenkins instance.",
                "valid": False
            }
        ]
