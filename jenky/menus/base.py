# -*- coding: utf-8 -*-

from workflow import ICON_WARNING

from jenky import QUERY_DELIMITER

class BaseMenu(object):

    delimiter = QUERY_DELIMITER

    str_format = {
        "del": QUERY_DELIMITER
    }

    @property
    def items(self):
        return [
            {
                "title": "BaseMenu items must be subclass!",
                "subtitle": "You should probably never see this...",
                "valid": False,
                "icon": ICON_WARNING
            }
        ]

    def __init__(self, wf):
        self.wf = wf

    def set_menu(self):
        for item in self.items:
            self.wf.add_item(**item)
        self.wf.send_feedback()