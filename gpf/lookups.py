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

.. automethod:: gpf.lookups._process_row
"""

import typing as _tp

import gpf.common.const as _const
import gpf.common.textutils as _tu
import gpf.common.validate as _vld
import gpf.cursors as _cursors
import gpf.tools.geometry as _geo
import gpf.tools.metadata as _meta
import gpf.tools.queries as _q

_DUPEKEYS_ARG = 'duplicate_keys'
_MUTABLE_ARG = 'mutable_values'
_ROWFUNC_ARG = 'row_func'

#: The default (Esri-recommended) resolution that is used by the :func:`get_nodekey` function (i.e. for lookups).
#: If coordinate values fall within this distance, they are considered equal.
#: Set this to a higher or lower value (coordinate system units) if required.
XYZ_RESOLUTION = 0.0001


def get_nodekey(*args) -> _tp.Tuple[int]:
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
                    within the default resolution distance from each other (0.0001 units e.g. meters).
                    If the default resolution needs to be changed, set the ``XYZ_RESOLUTION`` constant beforehand.

    Example:

        >>> coord_lookup = ValueLookup('C:/Temp/test.gdb/my_points', 'SHAPE@XY', 'GlobalID')
        >>> coord = (4.2452, 23.24541)
        >>> key = key(*coord)
        >>> print(key)
        (42451, 232454)
        >>> coord_lookup.get(key)
        '{628ee94d-2063-47be-b57f-8c2af6345d4e}'

    :param args:    A minimum of 2 numeric values, an EsriJSON dictionary, an ArcPy Point or PointGeometry instance.
    """
    return tuple(int(v / XYZ_RESOLUTION) for v in _geo.get_xyz(*args) if v is not None)


def get_coordtuple(node_key: _tp.Tuple[int]) -> _tp.Tuple[float]:
    """
    This function converts a node key (created by :func:`get_nodekey`) of integer tuples
    back into a floating point coordinate X, Y(, Z) tuple.

    .. warning::    This function should **only** be used to generate output for printing/logging purposes or to create
                    approximate coordinates. Because :func:`get_nodekey` truncates the coordinate, it is impossible
                    to get the same coordinate value back as the one that was used to create the node key, which means
                    that some accuracy will be lost in the process.

    :param node_key:    The node key (tuple of integers) that has to be converted.
    :rtype:             tuple
    """
    return tuple((v * XYZ_RESOLUTION) for v in node_key)


# noinspection PyUnusedLocal
def _process_row(lookup: dict, row: _tp.Sequence, **kwargs) -> _tp.Union[str, None]:
    """
    The default row processor function used by the :class:`Lookup` class.
    Alternative row processor functions are implemented by the other lookup classes (e.g. :class:`ValueLookup`).

    :param lookup:  A reference to the lookup dictionary.
                    If the process_row() function is built in to a lookup class, *lookup* refers to *self*.
    :param row:     The current row tuple (as returned by a :class:`SearchCursor`).
    :param kwargs:  Optional user-defined keyword arguments.
    :rtype:         None, str, unicode

    .. note::       This "private" function is documented here, so that users can see its signature and behaviour.
                    However, users should **not** call this function directly, but define their own functions
                    based on this one, using the same function signature.

                    Row processor functions directly manipulate (i.e. populate) the dictionary.
                    Typically, this function should at least add a key and value(s) to the *lookup* dictionary.

                    **A row function should always return ``None``, unless the user wants to terminate the lookup.**
                    In that case, a failure reason (message) should be returned.
    """
    key, v = row[0], row[1:] if len(row) > 2 else row[1]
    if key is None:
        return
    lookup[key] = v


class Lookup(dict):
    """
    Lookup(table_path, key_field, value_field(s), {where_clause}, {**kwargs})

    Base class for all lookups.

    This class can be instantiated directly, but typically, a user would create a custom lookup class based on
    this one and then override the :func:`Lookup._process_row` method.
    Please refer to other implementations (:class:`RowLookup`, :class:`ValueLookup`) for concrete examples.

    **Params:**

    -   **table_path** (str, unicode):

        Full source table or feature class path.

    -   **key_field** (str, unicode):

        The field to use for the lookup dictionary keys.
        If *SHAPE@X[Y[Z]]* is used as the key field, the coordinates are "hashed" using the
        :func:`gpf.lookups.get_nodekey` function.
        This means, that the user should use this function as well in order to
        to create a coordinate key prior to looking up the matching value for it.

    -   **value_fields** (list, tuple, str, unicode):

        The field or fields to include as the lookup dictionary value(s), i.e. row.
        This is the value (or tuple of values) that is returned when you perform a lookup by key.

    -   **where_clause** (str, unicode, :class:`gpf.tools.queries.Where`):

        An optional where clause to filter on.

    **Keyword params:**

    -   **row_func**:

        If the user wishes to call the standard `Lookup` class but simply wants to use
        a custom row processor function, you can pass in this function using the keyword *row_func*.

    :raises RuntimeError:       When the lookup cannot be created or populated.
    :raises ValueError:         When a specified lookup field does not exist in the source table,
                                or when multiple value fields were specified.
    """

    def __init__(self, table_path: str, key_field: str, value_fields: _tp.Union[str, _tp.Sequence[str]],
                 where_clause: _tp.Union[str, _q.Where, None] = None, **kwargs):
        super().__init__()

        fields = tuple([key_field] + list(value_fields if _vld.is_iterable(value_fields) else (value_fields, )))
        self._hascoordkey = key_field.upper().startswith(_const.FIELD_X)
        self._populate(table_path, fields, where_clause, **kwargs)

    @staticmethod
    def _get_fields(table_path: str) -> _tp.List[str]:
        """
        Gets all field names in the table.

        :raises RuntimeError:   When the table metadata could not be retrieved.
        """
        desc = _meta.Describe(table_path)
        _vld.pass_if(desc, RuntimeError, f'Failed to create lookup for {_tu.to_repr(table_path)}')
        return desc.get_fields(True, True)

    @staticmethod
    def _check_fields(user_fields: _tp.Iterable[str], table_fields: _tp.Iterable[str]):
        """
        Checks if the given *user_fields* exist in *table_fields*.

        :raises ValueError: When a field does not exist in the source table.
        """
        for field in user_fields:
            _vld.pass_if(_const.CHAR_AT in field or field.upper() in table_fields,
                         ValueError, 'Field {} does not exist'.format(field))

    @staticmethod
    def _has_self(row_func):
        """ Checks if `func` is an instance method or function and checks if it's a valid row processor. """
        if _vld.signature_matches(row_func, Lookup._process_row):
            # row_func is an instance method (signature matches the default self._process_row())
            return True
        elif _vld.signature_matches(row_func, _process_row):
            # row_func is a regular function (signature matches _process_row())
            return False
        else:
            raise ValueError('Row processor function has a bad signature')

    def _process_row(self, row, **kwargs):
        """ Instance method version of the :func:`_process_row` module function. """
        return _process_row(self, row, **kwargs)

    def _populate(self, table_path, fields, where_clause=None, **kwargs):
        """ Populates the lookup with data, calling _process_row() on each row returned by the SearchCursor. """
        try:
            # Validate fields
            self._check_fields(fields, self._get_fields(table_path))

            # Validate row processor function (if any)
            row_func = kwargs.get(_ROWFUNC_ARG, self._process_row)
            has_self = self._has_self(row_func)

            with _cursors.SearchCursor(table_path, fields, where_clause) as rows:
                for row in rows:
                    failed = row_func(row, **kwargs) if has_self else row_func(self, row, **kwargs)
                    if failed:
                        raise Exception(failed)

        except Exception as e:
            raise RuntimeError('Failed to create {} for {}: {}'.format(self.__class__.__name__,
                                                                       _tu.to_repr(table_path), e))


class ValueLookup(Lookup):
    """
    ValueLookup(table_path, key_field, value_field, {where_clause}, {duplicate_keys})

    Creates a lookup dictionary from a given source table or feature class.
    ValueLookup inherits from ``dict``, so all the built-in dictionary functions
    (:func:`update`, :func:`items` etc.) are available.

    When an empty key (``None``) is encountered, the key-value pair will be discarded.

    **Params:**

    -   **table_path** (str, unicode):

        Full source table or feature class path.

    -   **key_field** (str, unicode):

        The field to use for the ValueLookup dictionary keys.
        If *SHAPE@X[Y[Z]]* is used as the key field, the coordinates are "hashed" using the
        :func:`gpf.lookups.get_nodekey` function.
        This means, that the user should use this function as well in order to
        to create a coordinate key prior to looking up the matching value for it.

    -   **value_field** (str, unicode):

        The single field to include in the ValueLookup dictionary value.
        This is the value that is returned when you perform a lookup by key.

    -   **where_clause** (str, unicode, :class:`gpf.tools.queries.Where`):

        An optional where clause to filter the table.

    **Keyword params:**

    -   **duplicate_keys** (bool):

        If ``True``, the ValueLookup allows for duplicate keys in the input.
        The dictionary values will become **lists** of values instead of a **single** value.
        Please note that actual duplicate checks will not be performed. This means, that
        when *duplicate_keys* is ``False`` and duplicates *are* encountered,
        the last existing key-value pair will be overwritten.

    :raises RuntimeError:       When the lookup cannot be created or populated.
    :raises ValueError:         When a specified lookup field does not exist in the source table,
                                or when multiple value fields were specified.

    .. seealso::                When multiple fields should be stored in the lookup,
                                the :class:`gpf.lookups.RowLookup` class should be used instead.
    """

    def __init__(self, table_path: str, key_field: str, value_field: str,
                 where_clause: _tp.Union[None, str, _q.Where] = None, **kwargs):
        _vld.raise_if(_vld.is_iterable(value_field), ValueError,
                      f'{ValueLookup.__name__} expects a single value field: use {RowLookup.__name__} instead')
        _vld.pass_if(all(_vld.has_value(v) for v in (table_path, key_field, value_field)), ValueError,
                     f'{ValueLookup.__name__} requires valid table_path, key_field and value_field arguments')

        # User cannot override row processor function for this class
        if _ROWFUNC_ARG in kwargs:
            del kwargs[_ROWFUNC_ARG]

        self._dupekeys = kwargs.get(_DUPEKEYS_ARG, False)
        super(ValueLookup, self).__init__(table_path, key_field, value_field, where_clause, **kwargs)

    def _process_row(self, row, **kwargs):
        """ Row processor function override. """
        key, value = row
        if key is None:
            return
        if self._hascoordkey:
            key = get_nodekey(*key)
        if self._dupekeys:
            v = self.setdefault(key, [])
            v.append(value)
        else:
            self[key] = value


class RowLookup(Lookup):
    """
    RowLookup(table_path, key_field, value_fields, {where_clause}, {duplicate_keys}, {mutable_values})

    Creates a lookup dictionary from a given table or feature class.
    RowLookup inherits from ``dict``, so all the built-in dictionary functions
    (:func:`update`, :func:`items` etc.) are available.

    When an empty key (``None``) is encountered, the key-values pair will be discarded.

    **Params:**

    -   **table_path** (str, unicode):

        Full source table or feature class path.

    -   **key_field** (str, unicode):

        The field to use for the RowLookup dictionary keys.
        If *SHAPE@X[Y[Z]]* is used as the key field, the coordinates are "hashed" using the
        :func:`gpf.tools.lookup.get_nodekey` function.
        This means, that the user should use this function as well in order to
        to create a coordinate key prior to looking up the matching values for it.

    -   **value_field** (str, unicode):

        The fields to include in the RowLookup dictionary values.
        These are the values that are returned when you perform a lookup by key.

    -   **where_clause** (str, unicode, :class:`gpf.tools.queries.Where`):

        An optional where clause to filter the table.

    **Keyword params:**

    -   **duplicate_keys** (bool):

        If ``True``, the RowLookup allows for duplicate keys in the input.
        The values will become **lists** of tuples/lists instead of a **single** tuple/list.
        Please note that duplicate checks will not actually be performed. This means, that
        when *duplicate_keys* is ``False`` and duplicates are encountered,
        the last existing key-value pair will be simply overwritten.

    -   **mutable_values** (bool):

        If ``True``, the RowLookup values are stored as ``list`` objects.
        These are mutable, which means that you can change the values or add new ones.
        The default is ``False``, which causes the RowLookup values to become ``tuple`` objects.
        These are immutable, which consumes less memory and allows for faster retrieval.

    :raises RuntimeError:       When the lookup cannot be created or populated.
    :raises ValueError:         When a specified lookup field does not exist in the source table,
                                or when a single value field was specified.

    .. seealso::                When a single field value should be stored in the lookup,
                                the :class:`gpf.lookups.ValueLookup` class should be used instead.
    """

    def __init__(self, table_path: str, key_field: str, value_fields: _tp.Sequence[str],
                 where_clause: _tp.Union[None, str, _q.Where] = None, **kwargs):
        _vld.raise_if(len(value_fields) <= 1, ValueError,
                      f'{RowLookup.__name__} expects multiple value fields: use {ValueLookup.__name__} instead')
        _vld.pass_if(all(_vld.has_value(v) for v in (table_path, key_field, value_fields[0])), ValueError,
                     f'{RowLookup.__name__} requires valid table_path, key_field and value_fields arguments')

        # User cannot override row processor function for this class
        if _ROWFUNC_ARG in kwargs:
            del kwargs[_ROWFUNC_ARG]

        self._dupekeys = kwargs.get(_DUPEKEYS_ARG, False)
        self._rowtype = list if kwargs.get(_MUTABLE_ARG, False) else tuple
        super(RowLookup, self).__init__(table_path, key_field, value_fields, where_clause, **kwargs)

        self._fieldmap = {name.lower(): i for i, name in enumerate(value_fields)}

    def _process_row(self, row, **kwargs):
        """ Row processor function override. """
        key, values = row[0], self._rowtype(row[1:])
        if key is None:
            return
        if self._hascoordkey:
            key = get_nodekey(*key)
        if self._dupekeys:
            v = self.setdefault(key, [])
            v.append(values)
        else:
            self[key] = values

    def get_value(self, key, field, default=None):
        """
        Looks up a value by key for one specific field.
        This function can be convenient when only a single value needs to be retrieved from the lookup.
        The difference with the built-in :func:`get` method is, that the :func:`get_value` function
        returns a single value, whereas the other one returns a list or tuple of values (i.e. row).

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

            >>> # Approach using the get_value() function:
            >>> print(my_lookup.get_value('{628ee94d-2063-47be-b57f-8c2af6345d4e}', 'Field1'))
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


class NodeSet(set):
    """
    Builds a set of unique node keys for coordinates in a feature class.
    The :func:`get_nodekey` function will be used to generate the coordinate hash.
    When the feature class is Z aware, the node keys will be 3D as well.
    Note that in all cases, M will be ignored.

    The ``NodeSet`` inherits all methods from the built-in Python ``set``.

    For feature classes with a geometry type other than Point, a NodeSet will be built from the first and last
    points in a geometry. If this is not desired (i.e. all coordinates should be included), the user should set
    the *all_vertices* option to ``True``.
    An exception to this behavior is the Multipoint geometry: for this type, all coordinates will always be included.

    **Params:**

    -   **fc_path** (str):

        The full path to the feature class.

    -   **where_clause** (str, unicode, gpf.tools.queries.Where):

        An optional where clause to filter the feature class.

    -   **all_vertices** (bool):

        Defaults to ``False``. When set to ``True``, all geometry coordinates are included.
        Otherwise, only the first and/or last points are considered.

    :raises ValueError:     If the input dataset is not a feature class or if the geometry type is MultiPatch.
    """

    def __init__(self, fc_path: str, where_clause: _tp.Union[None, str, _q.Where] = None, all_vertices: bool = False):
        super().__init__()
        self._populate(fc_path, where_clause, all_vertices)

    @staticmethod
    def _get_desc(fc_path):
        # Checks if the input dataset is valid and returns its Describe object
        desc = _meta.Describe(fc_path)
        if not desc.shapeType:
            raise ValueError(f'Input dataset {_tu.to_repr(fc_path)} is not a feature class')
        if desc.is_multipatchclass:
            raise ValueError(f'Geometry type of {_tu.to_repr(fc_path)} is not supported')
        return desc

    def _fix_params(self, fc_path, all_vertices):
        """
        Returns a tuple of (field, all_vertices) based on the input parameters.
        The shape type of the feature class sets the field name and may override *oll_vertices*.
        """

        # The fastest way to fetch results is by reading coordinate tuples
        desc = self._get_desc(fc_path)
        field = _const.FIELD_XYZ if desc.hasZ else _const.FIELD_XY
        if not desc.is_pointclass:
            # However, for geometry types other than Point, we need to read the Shape object
            field = _const.FIELD_SHAPE
        if desc.is_multipointclass:
            # Multipoints will be treated differently (always read all vertices)
            all_vertices = True

        return field, all_vertices

    def _populate(self, fc_path, where_clause, all_vertices):
        """ Populates the NodeSet with node keys. """

        field, all_vertices = self._fix_params(fc_path, all_vertices)

        # Iterate over all geometries and add keys
        with _cursors.SearchCursor(fc_path, field, where_clause) as rows:
            for shape, in rows:
                # If the geometry is a simple coordinate tuple, immediately add it
                if field.startswith(_const.FIELD_XY):
                    self.add(get_nodekey(*shape))
                    continue

                if all_vertices:
                    for coord in _geo.get_vertices(shape):
                        self.add(get_nodekey(*coord))
                    continue

                # When *all_vertices* is False (or the geometry is not a Multipoint), only get the start/end nodes
                self.add(get_nodekey(shape.firstPoint))
                self.add(get_nodekey(shape.lastPoint))


class ValueSet(frozenset):
    """
    Builds a set of unique values for a single column in a feature class or table.
    This class inherits all methods from the built-in Python ``frozenset``.

    **Params:**

    -   **table_path** (str):

        The full path to the table or feature class.

    -   **field** (str):

        The field name for which to collect a set of unique values.

    -   **where_clause** (str, gpf.tools.queries.Where):

        An optional where clause to filter the feature class.
    """

    def __new__(cls, table_path: str, field, where_clause: _tp.Union[None, str, _q.Where] = None):
        # Populate the frozenset
        with _cursors.SearchCursor(table_path, field, where_clause) as rows:
            return super(ValueSet, cls).__new__(cls, (value for value, in rows))

    # noinspection PyMissingConstructor, PyUnusedLocal
    def __init__(self, table_path, field, where_clause=None):
        # This override is only required for type hint purposes and to match __new__'s signature
        pass
