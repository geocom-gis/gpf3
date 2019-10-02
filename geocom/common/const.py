# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

"""
Module with global constants that are used throughout the Geocom package.
"""

import locale as _locale
import sys as _sys

POSIX = 'win' not in _sys.platform
DEFAULT_ENCODING = _locale.getpreferredencoding()
UTF8_ENCODING = 'UTF-8'

EMPTY_STR = ''
EMPTY_OBJ = object()

ARCPY = 'arcpy'
