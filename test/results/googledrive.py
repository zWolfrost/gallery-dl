# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

from gallery_dl.extractor import googledrive


__tests__ = (
{
    "#url"         : "https://drive.google.com/drive/folders/1J67pW33Y4o74DmZPh87SOcbz8xft8A-w",
    "#category"    : ("", "googledrive", "folder"),
    "#class"       : googledrive.GoogledriveFolderExtractor,
    "#count"       : 7,
    "#recursive"   : False,

    "date_modified": "type:datetime",
    "date_uploaded": "type:datetime",
    "filename"     : str,
    "mime"         : str,
    "num"          : int,
    "size"         : int,
    "type"         : "file",
    "url"          : str,
},

{
    "#url"         : "https://drive.google.com/drive/folders/1AMVYyifpM-rK6MrA3n13nWTMgJwc2trm",
    "#category"    : ("", "googledrive", "folder"),
    "#class"       : googledrive.GoogledriveFolderExtractor,
    "#count"       : 4,

    "date_modified": "type:datetime",
    "date_uploaded": "type:datetime",
    "filename"     : str,
    "mime"         : str,
    "num"          : int,
    "size"         : int,
    "type"         : "file",
    "url"          : str,
},

{
    "#url"         : "https://drive.google.com/file/d/1-56l7Su4YXi53kjfrxOyQzO6gxvIoxWM/view",
    "#category"    : ("", "googledrive", "file"),
    "#class"       : googledrive.GoogledriveFileExtractor,
    "#count"       : 1,

    "filename"     : "100MB.bin",
    "mime"         : "application/octet-stream",
    "type"         : "file",
    "url"          : "https://drive.usercontent.google.com/download?id=1-56l7Su4YXi53kjfrxOyQzO6gxvIoxWM&export=download&confirm=t",
},

)
