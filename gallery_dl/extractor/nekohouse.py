# -*- coding: utf-8 -*-

# Copyright 2021 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://nekohouse.su/"""

from .common import Extractor, Message
from .. import text

BASE_PATTERN = r"(?:https?://)?nekohouse\.su"


class NekohouseExtractor(Extractor):
    """Base class for nekohouse extractors"""
    category = "nekohouse"
    root = "https://nekohouse.su"
    directory_fmt = ("{category}", "{service}", "{user}")
    filename_fmt = "{id}_{title[:180]}_{num:>02}_{filename[:180]}.{extension}"
    archive_fmt = "{service}_{user}_{id}_{num}"

    user_url_fmt = "https://nekohouse.su/{}/user/{}"
    post_url_fmt = "https://nekohouse.su/{}/user/{}/post/{}"

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.match = match

    def yield_post(self, url):
        page = self.request(url).text
        page_extractor = text.extract_from(page)
        service, _, user, _, id = url.split("/")[3:]

        published = page_extractor(
            'name="published" content="', '"'
        )
        title = page_extractor(
            'class="scrape__title">\n            <span>', '</span>'
        )
        content = page_extractor(
            '<div class="scrape__content">\n      ', '\n    </div>'
        )

        urls = [
            self.root + "/data/" + path
            for path in text.extract_iter(page, 'href="/data/', '"')
        ]

        post = {
            "service": service,
            "user": text.parse_int(user),
            "id": text.parse_int(id),
            "title": text.unescape(title),
            "content": content,
            "date": text.parse_datetime(published, "%Y-%m-%d %H:%M:%S+00:00")
        }

        for num, url in enumerate(urls, 1):
            yield Message.Url, url, text.nameext_from_url(
                url, {**post, "num": num}
            )


class NekohouseUserExtractor(NekohouseExtractor):
    """Extractor for all posts from a nekohouse.su user listing"""
    subcategory = "user"
    pattern = BASE_PATTERN + r"/([^/?#]+)/user/(\d+)/?(?:$|[?#])(?:o=(\d*))?"

    def items(self):
        service, user, offset = self.match.groups()
        offset = int(offset or 0)

        yield Message.Directory, {
            "category": self.category,
            "service": service,
            "user": user,
        }

        post_count = -1
        while post_count != 0:
            page = self.request(
                self.user_url_fmt.format(service, user),
                params={"o": offset}
            ).text

            post_count = 0
            for id in text.extract_iter(
                page, 'href="/{}/user/{}/post/'.format(service, user), '"'
            ):
                post_count += 1
                yield from self.yield_post(
                    self.post_url_fmt.format(service, user, id)
                )

            offset += 50


class NekohousePostExtractor(NekohouseExtractor):
    """Extractor for a single nekohouse.su post"""
    subcategory = "post"
    pattern = BASE_PATTERN + r"/([^/?#]+)/user/(\d+)/post/(\d+)"

    def items(self):
        service, user, id = self.match.groups()
        yield Message.Directory, {
            "category": self.category,
            "service": service,
            "user": user,
        }

        post_url = self.post_url_fmt.format(service, user, id)
        yield from self.yield_post(post_url)
