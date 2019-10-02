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
This module can be used to build lookup data structures from Esri tables and feature classes.
"""

import typing as _tp
from abc import ABCMeta
from abc import abstractmethod

import gpf.common.textutils as _tu
import gpf.common.validate as _vld
import gpf.tools.cursors as _cursors
import gpf.tools.metadata as _metadata
import gpf.tools.queries as _queries

_DUPEKEYS_ARG = 'duplicate_keys'
_MUTABLE_ARG = 'mutable_values'
_SINGLEVAL_ARG = 'single_value'

_FLD_SHAPEXY = 'SHAPE@XY'

#: The default (Esri-recommended) resolution that is used by the :func:`coord_key` function (i.e. for lookups).
#: If coordinate values fall within this distance, they are considered equal.
#: Set this to a higher or lower value (metric units) if required.
XYZ_RESOLUTION = 0.0001


def coord_key(x: _tp.Union[int, float], y: _tp.Union[int, float], z: _tp.Union[int, float] = None) -> _tp.Tuple[int]:
    """
    This function creates a hash-like tuple that can be used as a key in a :class:`RowLookup` or
    :class:`ValueLookup` dictionary.
    The tuple does not contain actual hashes, but consists of 2 or 3 (long) integers, which essentially are created by
    dividing the coordinate values by the default resolution (0.0001) and truncating them to an integer.

    Whenever a lookup is created using `SHAPE@XY` or `SHAPE@XYZ` as the *key_field*, this function is automatically
    used to generate a key for the coordinate. If the user has a coordinate and wants to find the matching value(s)
    in the lookup, the coordinate must be turned into a key first using this function.

    .. note::       The number of dimensions of the coordinate must match the ones in the lookup.
                    In other words, when a lookup was built using 2D coordinates, the lookup key must be 2D as well.

    .. warning::    This function has been tested on 10 million random points and no duplicate keys were encountered.
                    However, bear in mind that 2 nearly identical coordinates might share the same key if they lie
                    within the default resolution distance from each other (0.0001 meter).
                    If the default resolution needs to be changed, set the ``XYZ_RESOLUTION`` constant beforehand.

    Example:

        >>> coord_lookup = ValueLookup('C:/Temp/test.gdb/my_points', 'SHAPE@XY', 'GlobalID')
        >>> coord = (4.2452, 23.24541)
        >>> key = key(*coord)
        >>> print(key)
        (42451, 232454)
        >>> coord_lookup.get(coord_key)
        '{628ee94d-2063-47be-b57f-8c2af6345d4e}'

    :param x:   The X value of the coordinate.
    :param y:   The Y value of the coordinate.
    :param z:   An optional Z value of the coordinate (if 3D).
    """
    return tuple(int(v / XYZ_RESOLUTION) for v in (x, y, z) if v is not None)


class _BaseLookup(dict):
    """
    Abstract base class for all lookups.
    Refer to the implementations (RowLookup, ValueLookup) for documentation.
    """
    __metaclass__ = ABCMeta

    def __init__(self, table_path: str, key_field: str, value_fields: _tp.Union[str, _tp.Iterable[str]], **kwargs):
        super().__init__()

        fields = tuple([key_field] + list(value_fields if _vld.is_iterable(value_fields) else (value_fields, )))
        self._iscoordkey = key_field.upper().startswith(_FLD_SHAPEXY)
        self._populate(table_path, fields, where_clause, **kwargs)

    @staticmethod
    def _get_fields(table_path: str) -> _tp.List[str]:
        """
        Gets all field names in the table.

        :raises RuntimeError:   When the table metadata could not be retrieved.
        """
        desc = _metadata.Describe(table_path)
        _vld.raise_if(desc.error, RuntimeError,
                      'Failed to create lookup for {}: {}'.format(_tu.to_repr(table_path), desc.error))
        return desc.fields(True, True)

    @staticmethod
    def _check_fields(user_fields: _tp.Iterable[str], table_fields: _tp.Iterable[str]):
        """
        Checks if the given *user_fields* exist in *table_fields*.

        :raises ValueError: When a field does not exist in the source table.
        """
        for field in user_fields:
            _vld.pass_if('@' in field or field.upper() in table_fields,
                         ValueError, 'Field {} does not exist'.format(field))

    @staticmethod
    def _parse_kwargs(**kwargs) -> _tp.Tuple[bool, bool]:
        """
        Returns a tuple of (bool, bool) for the _populate() function.
        """
        dupe_keys = kwargs.get(_DUPEKEYS_ARG, False)
        is_mutable = kwargs.get(_MUTABLE_ARG, False)
        return dupe_keys, is_mutable

    @abstractmethod
    def _populate(self, table_path: str, fields: _tp.Iterable[str],
                  where_clause: _tp.Union[None, str, _queries.Where] = None, **kwargs):
        """ Abstract method to populate the lookup. """
        pass


class ValueLookup(_BaseLookup):
    """
    ValueLookup(table_path, key_field, value_field, {where_clause}, {duplicate_keys})

    Creates a lookup dictionary from a given source table or feature class.
    ValueLookup inherits from ``dict``, so all the built-in dictionary functions
    (:func:`update`, :func:`items` etc.) are available.

    When an empty key (``None``) is encountered, the key-value pair will be discarded.

    :param table_path:          Full source table or feature class path.
    :param key_field:           The field to use for the ValueLookup dictionary keys.
                                If `SHAPE@XY` is used as the key field, the coordinates are "hashed" using the
                                :func:`gpf.tools.lookup.coord_key` function.
                                This means, that the user should use this function as well in order to
                                to create a coordinate key prior to looking up the matching value for it.
    :param value_field:         The single field to include in the ValueLookup dictionary value.
                                This is the value that is returned when you perform a lookup by key.
    :param where_clause:        An optional where clause to filter the table.
    :keyword duplicate_keys:    If ``True``, the ValueLookup allows for duplicate keys in the input.
                                The dictionary values will become **lists** of values instead of a **single** value.
                                Please note that actual duplicate checks will not be performed. This means, that
                                when *duplicate_keys* is ``False`` and duplicates *are* encountered,
                                the last existing key-value pair will be overwritten.
    :type table_path:           str
    :type key_field:            str
    :type value_field:          str
    :type where_clause:         str, gpf.tools.queries.Where
    :type duplicate_keys:       bool
    :raises RuntimeError:       When the lookup cannot be created or populated.
    :raises ValueError:         When a specified lookup field does not exist in the source table,
                                or when multiple value fields were specified.

    .. seealso::                When multiple fields should be stored in the lookup,
                                the :class:`gpf.tools.lookup.RowLookup` class should be used instead.
    """

    def __init__(self, table_path: str, key_field: str, value_field: str,
                 where_clause: _tp.Union[None, str, _queries.Where] = None, **kwargs):
        _vld.raise_if(_vld.is_iterable(value_field), ValueError,
                      '{} expects a single value field: use {} instead'.format(ValueLookup.__name__,
                                                                               RowLookup.__name__))
        _vld.pass_if(all(_vld.has_value(v) for v in (table_path, key_field, value_field)), ValueError,
                     '{} requires valid table_path, key_field and value_field arguments')
        super().__init__(table_path, key_field, value_field, where_clause, **kwargs)

    def _populate(self, table_path, fields, where_clause=None, **kwargs):
        """ Populates the ValueLookup dictionary. """
        try:
            self._check_fields(fields, self._get_fields(table_path))
            dupe_keys, _ = self._parse_kwargs(**kwargs)
            for key, value in _cursors.SearchCursor(table_path, fields, where_clause):
                if key is None:
                    continue
                if self._iscoordkey:
                    key = coord_key(*key)
                if dupe_keys:
                    v = self.setdefault(key, [])
                    v.append(value)
                else:
                    self[key] = value
        except Exception as e:
            raise RuntimeError('Failed to create {} for {}: {}'.format(ValueLookup.__name__,
                                                                       _tu.to_repr(table_path), e))


class RowLookup(_BaseLookup):
    """
    RowLookup(table_path, key_field, value_fields, {where_clause}, {duplicate_keys}, {mutable_values})

    Creates a lookup dictionary from a given table or feature class.
    RowLookup inherits from ``dict``, so all the built-in dictionary functions
    (:func:`update`, :func:`items` etc.) are available.

    When an empty key (``None``) is encountered, the key-values pair will be discarded.

    :param table_path:          Full table or feature class path.
    :param key_field:           The field to use for the RowLookup dictionary keys.
                                If `SHAPE@XY` is used as the key field, the coordinates are "hashed" using the
                                :func:`gpf.tools.lookup.coord_key` function.
                                This means, that the user should use this function as well in order to
                                to create a coordinate key prior to looking up the matching values for it.
    :param value_fields:        The fields to include in the RowLookup dictionary values.
                                These are the values that are returned when you perform a lookup by key.
    :param where_clause:        An optional where clause to filter the table.
    :keyword duplicate_keys:    If ``True``, the RowLookup allows for duplicate keys in the input.
                                The values will become **lists** of tuples/lists instead of a **single** tuple/list.
                                Please note that duplicate checks will not actually be performed. This means, that
                                when *duplicate_keys* is ``False`` and duplicates are encountered,
                                the last existing key-value pair will be simply overwritten.
    :keyword mutable_values:    If ``True``, the RowLookup values are stored as ``list`` objects.
                                These are mutable, which means that you can change the values or add new ones.
                                The default is ``False``, which causes the RowLookup values to become ``tuple`` objects.
                                These are immutable, which consumes less memory and allows for faster retrieval.
    :type table_path:           str
    :type key_field:            str
    :type value_fields:         list, tuple
    :type where_clause:         str, gpf.tools.queries.Where
    :type duplicate_keys:       bool
    :type mutable_values:       bool
    :raises RuntimeError:       When the lookup cannot be created or populated.
    :raises ValueError:         When a specified lookup field does not exist in the source table,
                                or when a single value field was specified.

    .. seealso::                When a single field value should be stored in the lookup,
                                the :class:`gpf.tools.lookup.ValueLookup` class should be used instead.
    """

    def __init__(self, table_path: str, key_field: str, value_fields: _tp.Iterable[str],
                 where_clause: _tp.Union[None, str, _queries.Where] = None, **kwargs):
        _vld.raise_if(len(value_fields) <= 1, ValueError, '{} expects multiple value fields: use {} instead'.format(
                RowLookup.__name__, ValueLookup.__name__))
        _vld.pass_if(all(_vld.has_value(v) for v in (table_path, key_field, value_fields[0])), ValueError,
                     '{} requires valid table_path, key_field and value_fields arguments')
        super().__init__(table_path, key_field, value_fields, where_clause, **kwargs)
        self._fieldmap = {name.lower(): i for i, name in enumerate(value_fields)}

    def _populate(self, table_path, fields, where_clause=None, **kwargs):
        """ Populates the RowLookup dictionary. """
        try:
            self._check_fields(fields, self._get_fields(table_path))
            dupe_keys, is_mutable = self._parse_kwargs(**kwargs)
            cast_type = list if is_mutable else tuple
            for row in _cursors.SearchCursor(table_path, fields, where_clause):
                key, values = row[0], cast_type(row[1:])
                if key is None:
                    continue
                if self._iscoordkey:
                    key = coord_key(*key)
                if dupe_keys:
                    v = self.setdefault(key, [])
                    v.append(values)
                else:
                    self[key] = values
        except Exception as e:
            raise RuntimeError('Failed to create {} for {}: {}'.format(RowLookup.__name__,
                                                                       _tu.to_repr(table_path), e))

    def get_fieldvalue(self, key: _tp.Any, field: str, default: _tp.Any = None) -> _tp.Any:
        """
        Looks up a value by key for a specific field name.
        This function can be convenient when only a single value needs to be retrieved from the lookup.

        Example:

            >>> my_lookup = RowLookup('C:/Temp/test.gdb/my_table', 'GlobalID', 'Field1', 'Field2')

            >>> # Traditional approach to print Field1:
            >>> values = my_lookup.get('{628ee94d-2063-47be-b57f-8c2af6345d4e}')
            >>> if values:
            >>>     print(values[0])
            'ThisIsTheValueOfField1'

            >>> # Alternative traditional approach to print Field1:
            >>> field1, field2 = my_lookup.get('{628ee94d-2063-47be-b57f-8c2af6345d4e}', (None, None))
            >>> if field1:
            >>>     print(field1)
            'ThisIsTheValueOfField1'

            >>> # Approach using the get_fieldvalue() function:
            >>> print(my_lookup.get_fieldvalue('{628ee94d-2063-47be-b57f-8c2af6345d4e}', 'Field1'))
            'ThisIsTheValueOfField1'

        :param key:     Key to find in the lookup dictionary.
        :param field:   The field name (as used during initialization of the lookup) for which to retrieve the value.
        :param default: The value to return when the value was not found. Defaults to ``None``.
        """

        row = self.get(key, ())
        try:
            return row[self._fieldmap[field.lower()]]
        except LookupError:
            return default
