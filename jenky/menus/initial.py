# -*- coding: utf-8 -*-

from jenky.menus.base import BaseMenu

class InitialMenu(BaseMenu):

    @property
    def items(self):
        return [
            {
                "title": "Welcome to Jenky!",
                "subtitle": "It looks like some things still need to be set configured.",
                "valid": False
            },
            {
                "title": "Go to settings menu.",
                "subtitle": "You'll need to configure username, api key, and hostname to get up and running.",
                "valid": True,
                "arg": "jenky-settings"
            }
        ]