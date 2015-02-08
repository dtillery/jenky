# -*- coding: utf-8 -*-
from workflow import ICON_WARNING

from jenky import QUERY_DELIMITER


class BaseMenu(object):

    query_match = None

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

    @property
    def output(self):
        return self.query

    def __init__(self, wf, query):
        self.wf = wf
        self.query = query
        self.log = self.wf.logger

    def set_menu(self):
        for item in self.items:
            self.wf.add_item(**item)
        self.wf.send_feedback()