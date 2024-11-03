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

    user_url_fmt = root + "/{}/user/{}"
    import_url_fmt = root + "/{}/user/{}/post/{}"
    post_url_fmt = root + "/post/{}"

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.match = match

    def yield_post(self, url):
        page = self.request(url).text
        page_extractor = text.extract_from(page)

        if len(url.split("/")) == 8:
            service, _, user, _, id = url.split("/")[3:]
            is_import = True
        else:
            service = user = None
            id = url.split("/")[-1]
            is_import = False


        username = text.unescape(page_extractor(
            '&#34; by ', ' from  | Nekohouse'
        ))
        date = text.parse_datetime(
            page_extractor('name="published" content="', '"'),
            "%Y-%m-%d %H:%M:%S+00:00"
        )
        title = text.unescape(page_extractor(
            'class="scrape__title">\n            <span>', '</span>'
        ))
        content = page_extractor(
            '<div class="scrape__content">\n      ', '\n    </div>'
        )

        urls = [
            self.root + "/data/" + path
            for path in text.extract_iter(page, 'href="/data/', '"')
        ]

        post = {
            "service": service or None,
            "user": user or None,
            "username": username or None,
            "id": text.parse_int(id),
            "title": title or None,
            "content": content or None,
            "date": date or None,
            "is_import": is_import
        }

        yield post

        for num, url in enumerate(urls, 1):
            yield text.nameext_from_url(
                url, {**post, "url": url, "num": num}
            )


class NekohouseUserExtractor(NekohouseExtractor):
    """Extractor for all posts from a nekohouse.su user listing"""
    subcategory = "user"
    pattern = BASE_PATTERN + r"/([^/?#]+)/user/([^/?#]+)(?:$|/(?!post/)(?:\?o=(\d*))?)"

    def items(self):
        service, user, offset = self.match.groups()
        offset = int(offset or 0)

        if offset % 50 != 0:
            raise ValueError("Offset must be a multiple of 50.")

        post_count = -1
        while post_count != 0:
            page = self.request(
                self.user_url_fmt.format(service, user),
                params={"o": offset}
            ).text

            post_count = 0
            for path in text.extract_iter(
                page, '"\n  >\n      <a href="', '"'
            ):
                yield_post = self.yield_post(self.root + path)

                yield Message.Directory, {
                    **next(yield_post),
                    "service": service,
                    "user": user
                }

                post_count += 1
                for post in yield_post:
                    yield Message.Url, post["url"], {
                        **post,
                        "is_thumbnail": post["url"].lstrip(self.root) in page
                    }

            offset += 50


class NekohousePostExtractor(NekohouseExtractor):
    """Extractor for a single nekohouse.su post"""
    subcategory = "post"
    pattern = BASE_PATTERN + r"/(?:([^/?#]+)/user/([^/?#]+)/)?post/([^/?#]+)"

    def items(self):
        service, user, id = self.match.groups()
        is_import = service and user

        post_url = self.import_url_fmt.format(service, user, id) \
            if is_import else self.post_url_fmt.format(id)

        yield_post = self.yield_post(post_url)

        yield Message.Directory, {
            **next(yield_post),
            "service": service,
            "user": user
        }

        for post in yield_post:
            yield Message.Url, post["url"], post
