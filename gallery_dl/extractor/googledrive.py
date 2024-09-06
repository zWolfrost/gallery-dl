# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://www.google.com/drive/"""

from .common import Extractor, Message
from .. import text

BASE_PATTERN = r"(?:https?://)drive\.google\.com"


class GoogledriveBase(Extractor):
    """Base class for Google Drive extractors"""
    category = "googledrive"
    root = "https://drive.google.com"
    filename_fmt = "{name[:180]} ({id}).{extension}"
    archive_fmt = "{name} ({id}).{extension}"

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.match = match

    def _init(self):
        self.recursive = self.config("recursive", False)

    def get_file_download_url(self, file):
        FILE_DOWNLOAD_URL = (
            "https://drive.usercontent.google.com"
            "/download?id={id}&export=download&confirm=t"
        )

        url = FILE_DOWNLOAD_URL.format(id=file["id"])

        if (not file.get("size")) or (file["size"] > 10*1024*1024):  # 10 MB
            headers = self.request(url, method="HEAD").headers
            if "Content-Disposition" not in headers:
                confirm_page = self.request(url)

                if '"at" value="' not in confirm_page.text:
                    uuid = text.extr(confirm_page.text, '"uuid" value="', '"')
                    confirm_page = self.request(url + "&uuid=" + uuid)

                at = text.extr(confirm_page.text, '"at" value="', '"')
                url += "&at=" + at

        # TODO: Handle quota exceeded error

        return url

    def item_filename_handle(self, item):
        if "." in item["filename"]:
            item["name"], _, item["extension"] = (
                item["filename"].rpartition(".")
            )
        else:
            item["name"] = item["filename"]
            item["extension"] = ""

    def item_mime_handle(self, item):
        DOCS_DOWNLOAD_URL = (
            "https://docs.google.com/{type}/d/{id}/export?format={format}"
        )
        DOCS_MIME_TYPES = {
            ("application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"):
                    {"type": "document", "format": "docx"},

            ("application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"):
                    {"type": "spreadsheets", "format": "xlsx"},

            ("application/vnd.openxmlformats-officedocument"
                ".presentationml.presentation"):
                    {"type": "presentation", "format": "pptx"},

            "application/vnd.google-apps.document":
                {"type": "document", "format": "docx"},

            "application/vnd.google-apps.kix":
                {"type": "document", "format": "docx"},

            "application/vnd.google-apps.spreadsheet":
                {"type": "spreadsheets", "format": "xlsx"},

            "application/vnd.google-apps.presentation":
                {"type": "presentation", "format": "pptx"},

            "application/vnd.google-apps.drawing":
                {"type": "drawings", "format": "png"}
        }

        if item["mime"] == "application/vnd.google-apps.folder":
            item["type"] = "folder"
            item["url"] = (
                "https://drive.google.com/drive/folders/" + item["id"]
            )
        elif "application/vnd.google-apps" in item["mime"]:
            item["type"] = "file"
            if item["mime"] in DOCS_MIME_TYPES:
                item["extension"] = DOCS_MIME_TYPES[item["mime"]]["format"]
                item["filename"] += "." + item["extension"]

                item["url"] = DOCS_DOWNLOAD_URL.format(
                    id=item["id"],
                    type=DOCS_MIME_TYPES[item["mime"]]["type"],
                    format=item["extension"]
                )
        else:
            item["type"] = "file"
            item["url"] = self.get_file_download_url(item)


class GoogledriveFileExtractor(GoogledriveBase):
    """Extractor for Google Drive files"""
    subcategory = "file"
    pattern = BASE_PATTERN + r"/file/d/([^/|?]+)"
    directory_fmt = ("{category}", "{name[:180]} ({id})")
    example = "https://drive.google.com/file/d/ID"

    def get_file_metadata(self, page):
        page_extr = text.extract_from(page)

        file = {
            "filename": text.unescape(page_extr(
                '"og:title" content="', '">'
            )),
            "mime": page_extr('docs-dm":', ',').split('"')[-2],
            "id": text.unescape(page_extr(
                '"https://drive.google.com/file/d/', '/'
            ))
        }

        self.item_filename_handle(file)
        self.item_mime_handle(file)

        return file

    def items(self):
        url = self.root + "/file/d/" + self.match.group(1)
        page = self.request(url).text
        file = self.get_file_metadata(page)

        yield Message.Directory, file

        if "url" in file:
            yield Message.Url, file["url"], file


class GoogledriveFolderExtractor(GoogledriveBase):
    """Base class for Google Drive Folder extractors"""
    subcategory = "folder"
    pattern = BASE_PATTERN + r"/drive/?.*?/folders/([^/|?]+)"
    directory_fmt = ("{category}", "{title[:180]} ({id})")
    example = "https://drive.google.com/drive/folders/ID"

    def get_folder_metadata_iter(self, page):
        directory = {
            "title": text.unescape(text.extr(
                page, '<title>', ' - Google Drive</title>'
            )),
            "id": text.extr(
                page, 'data-parent="', '"'
            )
        }

        yield directory

        items_raw_cwiz_data_iter = text.extract_iter(page, 'pmHCK', '</c-wiz>')
        items_raw_script_data = text.extr(
            page, "window.wiz_progress()", "window['_DRIVE_ivdc']()"
        )

        for i, item_cwiz_data in enumerate(items_raw_cwiz_data_iter):
            item = {
                "num": i + 1,
                "id": text.unescape(text.extr(
                    item_cwiz_data, 'data-id="', '"'
                )),
                "filename": text.unescape(text.extr(
                    item_cwiz_data, 'data-tooltip-unhoverable="true">', '<'
                )),
            }

            self.item_filename_handle(item)

            item_script_data = text.extr(
                items_raw_script_data,
                (item["id"] + "\\x22,\\x5b\\x22" +
                    directory["id"] + "\\x22\\x5d,"),
                ",\\x5b\\x5b1,"
            )

            item["mime"] = text.extr(
                item_script_data, ",\\x22", "\\x22"
            ).replace("\\/", "/")

            item["size"] = int(item_script_data.split(",")[-1])

            item_dates = list(map(
                lambda ms: text.parse_timestamp(ms[:-3]),
                item_script_data.split(",")[-5:-1]
            ))
            item["date_uploaded"] = item_dates[0]
            item["date_modified"] = item_dates[1]
            item["date_accessed"] = item_dates[3]

            self.item_mime_handle(item)

            yield item

    def items(self):
        url = self.root + "/drive/folders/" + self.match.group(1)
        page = self.request(url).text
        metadata_iter = self.get_folder_metadata_iter(page)

        yield Message.Directory, next(metadata_iter)

        folders = []
        for item in metadata_iter:
            if item["type"] == "folder":
                folders.append(item)
            elif "url" in item:
                yield Message.Url, item["url"], item

        if self.recursive and folders:
            for folder in folders:
                folder["_extractor"] = GoogledriveFolderExtractor
                yield Message.Queue, folder["url"], folder
