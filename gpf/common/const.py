# coding: utf-8
#
# Copyright 2019 Geocom Informatik AG / VertiGIS

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Module with global constants that are used throughout the :py:mod:`gpf` package.
"""

import locale as _locale

#: The default encoding that the system uses (derived from locale).
#: For most western Windows-based systems, this will be cp1252, for example.
ENC_DEFAULT = _locale.getpreferredencoding()
ENC_UTF8 = 'UTF-8'

# Name of the arcpy module
PYMOD_ARCPY = 'arcpy'

# Placeholder for an "empty" object (that is not None)
OBJ_EMPTY = object()

# Single text characters
CHAR_DOT = '.'
CHAR_SPACE = ' '
CHAR_UNDERSCORE = '_'
CHAR_ASTERISK = '*'
CHAR_HASH = '#'
CHAR_DASH = '-'
CHAR_AT = '@'
CHAR_EMPTY = ''
CHAR_COMMA = ','
CHAR_TAB = '\t'
CHAR_LF = '\n'
CHAR_CR = '\r'

# Commonly used texts (multiple chars), e.g. for concatenation
TEXT_AND = 'and'
TEXT_OR = 'or'
TEXT_COMMASPACE = CHAR_COMMA + CHAR_SPACE
TEXT_DUNDER = CHAR_UNDERSCORE * 2
TEXT_PLACEHOLDER = '{}'
TEXT_CRLF = CHAR_CR + CHAR_LF

# Describe property names that can be used across multiple modules.
# We list them here and not in tools.metadata to avoid cyclic import failures.
DESC_FIELD_OID = 'OIDFieldName'
DESC_FIELD_SHAPE = 'shapeFieldName'
DESC_FIELD_LENGTH = 'lengthFieldName'
DESC_FIELD_AREA = 'areaFieldName'
DESC_FIELD_GLOBALID = 'globalIDFieldName'
DESC_FIELD_RASTER = 'rasterFieldName'
DESC_FIELD_SUBTYPE = 'subtypeFieldName'
DESC_FIELD_CREATOR = 'creatorFieldName'
DESC_FIELD_CREATED = 'createdAtFieldName'
DESC_FIELD_EDITOR = 'editorFieldName'
DESC_FIELD_EDITED = 'editedAtFieldName'

# Non-exhaustive list of Describe data types (sometimes equal to dataset types)
DESC_TYPE_FEATURECLASS = 'FeatureClass'
DESC_TYPE_FEATUREDATASET = 'FeatureDataset'
DESC_TYPE_GEOMETRICNET = 'GeometricNetwork'
DESC_TYPE_MOSAICRASTER = 'MosaicDataset'
DESC_TYPE_RASTER = 'RasterDataset'
DESC_TYPE_TABLE = 'Table'

# Esri geometry types
SHP_POINT = 'Point'
SHP_MULTIPOINT = 'Multipoint'
SHP_POLYLINE = 'Polyline'
SHP_POLYGON = 'Polygon'
SHP_MULTIPATCH = 'MultiPatch'

# Shorthand names for Esri fields that should be resolved at runtime.
FIELD_OID = 'OID@'
FIELD_SHAPE = 'SHAPE@'
FIELD_AREA = 'SHAPE@AREA'
FIELD_LENGTH = 'SHAPE@LENGTH'
FIELD_OGCWKB = 'SHAPE@WKB'
FIELD_OGCWKT = 'SHAPE@WKT'
FIELD_ESRIJSON = 'SHAPE@JSON'
FIELD_CENTROID = 'SHAPE@TRUECENTROID'
FIELD_X = 'SHAPE@X'
FIELD_Y = 'SHAPE@Y'
FIELD_Z = 'SHAPE@Z'
FIELD_M = 'SHAPE@M'
FIELD_XY = 'SHAPE@XY'
FIELD_XYZ = 'SHAPE@XYZ'

# Default GlobalID field name
FIELD_GLOBALID = 'GLOBALID'

# Common file extensions
EXT_ESRI_SHP = '.shp'
EXT_ESRI_SDE = '.sde'
EXT_ESRI_GDB = '.gdb'
EXT_ESRI_MDB = '.mdb'
EXT_ESRI_ADB = '.accdb'
