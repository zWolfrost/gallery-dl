# -*- coding: utf-8 -*-

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

    def extract_post(self, url, override=lambda x: x):
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
        date = self.parse_datetime(
            page_extractor('name="published" content="', '"'),
            "%Y-%m-%d %H:%M:%S+00:00"
        )
        title = text.unescape(page_extractor(
            'class="scrape__title">\n            <span>', '</span>'
        ))
        content = page_extractor(
            '<div class="scrape__content">\n      ', '\n    </div>'
        )

        files = []

        for num, html in enumerate(
            text.extract_iter(page, 'href="/data/', '>'), start=1
        ):
            if not html:
                break

            path = html.split('"')[0]

            fileext = text.nameext_from_url(path)

            files.append({
                "url": self.root + "/data/" + path,
                "filename": text.unquote(text.nameext_from_url(
                    text.extr(html, 'download="', '"', path)
                )["filename"]),
                "hash": fileext["filename"],
                "extension": fileext["extension"],
                "num": num
            })

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

        yield Message.Directory, "", override(post)

        for file in files:
            yield Message.Url, file["url"], override({**post, **file})


class NekohouseUserExtractor(NekohouseExtractor):
    """Extractor for all posts from a nekohouse.su user listing"""
    subcategory = "user"
    pattern = BASE_PATTERN + r"/([^/?#]+)/user/([^/?#]+)/?(?:\?o=(\d+)?)?$"

    def items(self):
        service, user, offset = self.groups
        offset = int(offset or 0)

        if offset % 50 != 0:
            raise ValueError("Offset must be a multiple of 50.")

        has_extracted = True
        while has_extracted:
            has_extracted = False

            page = self.request(
                self.user_url_fmt.format(service, user),
                params={"o": offset}
            ).text

            OVERRIDES = {
                "service": service,
                "user": user,
                "username": text.extr(
                    page, '<meta name="artist_name" content="', '">'
                )
            }

            for path in text.extract_iter(
                page, '"\n  >\n      <a href="', '"'
            ):
                has_extracted = True

                def _override(post):
                    post.update(OVERRIDES)

                    if "url" in post:
                        post["is_thumbnail"] = (
                            post["url"].lstrip(self.root) in page
                        )

                    return post

                yield from self.extract_post(self.root + path, _override)

            offset += 50


class NekohousePostExtractor(NekohouseExtractor):
    """Extractor for a single nekohouse.su post"""
    subcategory = "post"
    pattern = BASE_PATTERN + r"/(?:([^/?#]+)/user/([^/?#]+)/)?post/([^/?#]+)"

    def items(self):
        service, user, id = self.groups
        is_import = service and user

        post_url = self.import_url_fmt.format(service, user, id) \
            if is_import else self.post_url_fmt.format(id)

        yield from self.extract_post(post_url)
