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
The *fields* module contains helper functions related to working with Esri Fields (GIS attributes).
"""
import typing as _tp

import gpf.tools.metadata as _meta
from gpf.tools import arcpy as _arcpy

OBJECTID = 'OID@'
SHAPE = 'SHAPE@'
SHAPE_AREA = 'SHAPE@AREA'
SHAPE_LENGTH = 'SHAPE@LENGTH'


def check_missing(table: str, fields: _tp.Iterable[str]) -> _tp.Iterable[str]:
    """
    Returns a list of missing fields for a specified table or feature class.
    The field names are case-insensitive.
    If an empty list is returned, all fields are accounted for.

    If one ore more expected field names are a "special field" (containing an '@' sign),
    these will be resolved to the actual field names.
    If this process fails, the field will be considered missing.

    :param table:   The table or feature class for which to check the fields.
    :param fields:  A list of fields that should be present in the table or feature class.
    """
    try:
        table_fields = [field.name.upper() for field in _arcpy.ListFields(table) or []]
    except (RuntimeError, TypeError, ValueError):
        return fields

    desc = None
    missing = []
    for f in fields:
        field = f.upper()
        if '@' in field:
            if desc is None:
                desc = _meta.SpecialFields(table)
            if (field == OBJECTID and not desc.objectid_field) or \
               (field.startswith(SHAPE) and not desc.shape_field) or \
               (field == SHAPE_LENGTH and not desc.length_field) or \
               (field == SHAPE_AREA and not desc.area_field):
                missing.append(f)
            continue
        if field not in table_fields:
            missing.append(f)

    return missing
