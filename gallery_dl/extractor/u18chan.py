# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://u18chan.com/"""

from .common import Extractor, Message
from .. import text

BASE_PATTERN = r"(?:https?://)?.*?u18chan\.com"


class U18chanThreadExtractor(Extractor):
    """Extractor for u18chan threads"""
    category = "u18chan"
    subcategory = "thread"
    root = "https://u18chan.com"
    directory_fmt = ("{category}", "{board}", "{thread}")
    filename_fmt = "{id}_{original_filename}"
    pattern = BASE_PATTERN + r"/board/u18chan/([^/]+)/topic/(\d+)"
    example = "https://u18chan.com/board/u18chan/fur/topic/12345"

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.board, self.thread = match.groups()

    def items(self):
        url = self.root + "/board/u18chan/{}/topic/{}".format(
            self.board, self.thread
        )
        page = self.request(url).text

        directory = {
            "board": self.board,
            "thread": self.thread
        }
        yield Message.Directory, directory

        posts_iter = text.extract_iter(
            page, '<table class="ReplyBoxTable', '<a name="'
        )
        for post in posts_iter:
            if 'class="FileDetails"' in post:
                attachment = text.extract_all(post, (
                    ("text", 'href="javascript:EditPost(', '\');"'),
                    ("id", 'name="postID" value="', '"'),
                    ("url", 'File: <a href="', '" '),
                    ("filename", '<u>', '</u>'),
                    ("size", '</a> - (', 'b, '),
                    ("width", '', 'x'),
                    ("height", '', ', '),
                    ("original_filename", '', ')')
                ))[0]
                attachment["text"] = text.unescape(
                    ",".join(attachment["text"].split(",")[4:-2])[2:-4]
                ).encode("utf-8").decode("unicode_escape")
                attachment["size"] = text.parse_bytes(attachment["size"])
                attachment["name"], attachment["extension"] \
                    = attachment["filename"].rsplit(".", 1)

                yield Message.Url, attachment["url"], attachment
