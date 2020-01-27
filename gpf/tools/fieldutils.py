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

.. seealso::    The :class:`gpf.tools.metadata.Describe` class has a :func:`gpf.tools.metadata.Describe.get_fields`
                and a :func:`gpf.tools.metadata.Describe.get_editable_fields` function, which might also be helpful.
"""

import typing as _tp

import gpf.common.const as _const
import gpf.common.validate as _vld
from gpf import arcpy as _arcpy

_DEFAULT_TYPE = 'TEXT'

#: Lookup dictionary to map ``Field`` types to the field types used in ArcPy's :func:`AddField` function.
FIELDTYPE_MAPPING = {
    'Text': _DEFAULT_TYPE,
    'Single': 'FLOAT',
    'Double': 'DOUBLE',
    'SmallInteger': 'SHORT',
    'Integer': 'LONG',
    'Date': 'DATE',
    'Blob': 'BLOB',
    'Raster': 'RASTER',
    'Guid': 'GUID'
}


def get_name(field: _arcpy.Field, uppercase: bool = False) -> str:
    """
    Retrieves the field name from a ``Field`` instance and optionally changes it to uppercase.

    :param field:       An :class:`arcpy.Field` instance.
    :param uppercase:   When ``True`` (default = ``False``), the returned name will be made uppercase.
    """
    return field.name.upper() if uppercase else field.name


def list_fields(obj: _tp.Union[str, _tp.Sequence], names_only: bool = True,
                uppercase: bool = False) -> _tp.List[_tp.Union[str, _arcpy.Field]]:
    """
    Returns a list of Field objects or field names for a given list of Field objects or a dataset.

    :param obj:             Dataset path or list of original ``Field`` instances.
    :param names_only:      When ``True`` (default), a list of field names instead of ``Field`` instances is returned.
    :param uppercase:       When ``True`` (default=``False``), the returned field names will be uppercase.
                            This does **not** apply when *names_only* is ``False`` and ``Field`` instances are returned.
    :return:                List of field names or ``Field`` instances.
    """
    # Get field list if input is not a list (or tuple)
    fields = obj
    if not _vld.is_iterable(obj):
        fields = _arcpy.ListFields(obj) or []

    return [get_name(field, uppercase) if names_only else field for field in fields]


def list_missing(table: str, expected_fields: _tp.Sequence[str]) -> _tp.Sequence[str]:
    """
    Returns a list of missing field **names** for a specified table or feature class.
    The expected field names are case-insensitive.
    If an empty list is returned, all fields are accounted for.

    If one ore more expected field names are a "special field" (containing an '@' sign),
    these will be resolved to the actual field names.
    If this process fails, the field will be considered missing.

    :param table:           The table or feature class for which to check the fields.
    :param expected_fields: A list of fields that should be present in the table or feature class.
    """

    table_fields = list_fields(table, True, True)

    desc = None
    missing = []
    for f in expected_fields:
        field = f.upper()
        if _const.CHAR_AT in field:
            if desc is None:
                # Only describe the input table (= time-consuming) if @ has been used in a field name and only once
                try:
                    # Use arcpy's built-in Describe function, to avoid cyclic imports (in metadata module)
                    desc = _arcpy.Describe(table)
                except (RuntimeError, OSError, AttributeError, ValueError, TypeError):
                    desc = object()
            if (field == _const.FIELD_OID and not getattr(desc, _const.DESC_FIELD_OID, None)) or \
               (field.startswith(_const.FIELD_SHAPE) and not getattr(desc, _const.DESC_FIELD_SHAPE, None)) or \
               (field == _const.FIELD_LENGTH and not getattr(desc, _const.DESC_FIELD_LENGTH, None)) or \
               (field == _const.FIELD_AREA and not getattr(desc, _const.DESC_FIELD_AREA, None)):
                missing.append(f)
            continue
        if field not in table_fields:
            missing.append(f)

    return missing


def has_field(table: str, field_name: str) -> bool:
    """
    Simple wrapper for the :func:`list_missing` function to check if a single field exists.

    :param table:
    :param field_name:
    :return:
    """
    return not list_missing(table, (field_name,))


def add_field(dataset: str, name: str, template_field: [_arcpy.Field, None] = None,
              alias: [str, None] = None) -> _arcpy.Result:
    """
    Adds a new field to a *dataset*, based off a *template_field* ``Field`` instance.
    All properties from the new field will be taken from this template field, except for the *name* (and *alias*).

    :param dataset:         The full path to the dataset (table, feature class) to which the field should be added.
    :param name:            The name of the field to add.
    :param template_field:  An optional template ``Field`` on which the new field should be based.
                            If no template field is specified, a default field of type TEXT is created.
    :param alias:           An optional alias name for the field. Defaults to ``None``.
    :raises ValueError:     If a template field was provided, but it's not a ``Field`` instance,
                            or if the template field is of an unsupported type (i.e. GlobalID, OID or Geometry).
    """

    field_type = _DEFAULT_TYPE
    field_alias = alias
    field_precision = None
    field_scale = None
    field_length = None
    field_is_nullable = None
    field_is_required = None
    field_domain = None
    if template_field:
        if not isinstance(template_field, _arcpy.Field):
            raise ValueError('Template field should be an ArcPy Field instance')
        field_type = FIELDTYPE_MAPPING.get(template_field.type)
        if not field_type:
            raise ValueError('Fields of type {} cannot be added'.format(template_field.type))
        field_precision = template_field.precision
        field_scale = template_field.scale
        field_length = template_field.length
        field_is_nullable = template_field.isNullable
        field_is_required = template_field.required
        field_domain = template_field.domain

    return _arcpy.AddField_management(dataset, name, field_type,
                                      field_precision, field_scale, field_length, field_alias,
                                      field_is_nullable, field_is_required, field_domain)
