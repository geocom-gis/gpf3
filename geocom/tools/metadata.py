# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

"""
The metadata module contains functions and classes that help describing data.
"""
import typing as _tp

import geocom.common.textutils as _tu
import geocom.tools.cursors as _cursors
from geocom.tools import arcpy as _arcpy

_ATTR_FIELDS = 'fields'


class SpecialFields(object):
    """
    Describe-like object for special/reserved Esri fields (e.g. Shape, ObjectID, Area, etc.).
    All the special field names are exposed as attributes on this object. If any of the field names do not exist
    for the specified table or feature class, its value remains ``None``.

    :param element:     The path to the table or feature class for which to retrieve the field names
                        or a ``Describe`` object.
    """

    FIELD_GLOBALID = 'globalIDFieldName'
    FIELD_OBJECTID = 'OIDFieldName'
    FIELD_SHAPE = 'shapeFieldName'
    FIELD_AREA = 'areaFieldName'
    FIELD_LENGTH = 'lengthFieldName'
    FIELD_RASTER = 'rasterFieldName'
    FIELD_SUBTYPE = 'subtypeFieldName'

    __slots__ = '_names',

    def __init__(self, element: _tp.Union[str, _arcpy.Describe]):
        self._names = {}
        meta = element if isinstance(element, (Describe, _arcpy.Describe)) else Describe(element)
        if hasattr(meta, 'error') and meta.error:
            return
        self._setnames(meta)

    def _setnames(self, describe):
        for esri_attr in (f for f in dir(self) if f.startswith('FIELD_')):
            self._names[esri_attr] = getattr(describe, esri_attr, None) or None

    # For some reason, PyCharm does not like dynamic properties, so we use explicit properties here

    @property
    def globalid_field(self) -> _tp.Union[str, None]:
        """ Global ID field name. """
        return self._names.get(self.FIELD_GLOBALID)

    @property
    def objectid_field(self) -> _tp.Union[str, None]:
        """ Object ID field name. """
        return self._names.get(self.FIELD_OBJECTID)

    @property
    def shape_field(self) -> _tp.Union[str, None]:
        """ Perimeter or polyline length field name. """
        return self._names.get(self.FIELD_SHAPE)

    @property
    def length_field(self) -> _tp.Union[str, None]:
        """ Perimeter or polyline length field name. """
        return self._names.get(self.FIELD_LENGTH)

    @property
    def area_field(self) -> _tp.Union[str, None]:
        """ Polygon area field name. """
        return self._names.get(self.FIELD_AREA)

    @property
    def raster_field(self) -> _tp.Union[str, None]:
        """ Raster field name. """
        return self._names.get(self.FIELD_RASTER)

    @property
    def subtype_field(self) -> _tp.Union[str, None]:
        """ Subtype field name. """
        return self._names.get(self.FIELD_SUBTYPE)


# noinspection PyPep8Naming
class Describe(object):
    """
    Wrapper class for the ArcPy ``Describe`` object.
    This allows users to safely call Describe properties without errors, also when a property does not exist.
    If a property does not exist, it will return ``None``. If this is not desired,
    consider using the :func:`get` function, which behaves similar to a ``dict.get()``.

    :param element:     The data element to describe.
    :param as_dict:     If ``True``, the Data Access module of ArcPy will be used to describe the object.
                        This will not return a Describe object, but a dictionary (Python 3 only).
                        Dictionary keys can be accessed like object properties using this wrapper class.
                        The default is ``False``.
    """
    __slots__ = '_obj', '_error'

    def __init__(self, element, as_dict: bool = False):
        self._error = None
        try:
            self._obj = _arcpy.da.Describe(element) if as_dict else _arcpy.Describe(element)
        except (OSError, RuntimeError, _arcpy.ExecuteError, AttributeError) as e:
            self._error = e
            self._obj = {} if as_dict else None

    def __getattr__(self, item):
        """ Returns the property value of a Describe object item. """
        if isinstance(self._obj, dict):
            return self._obj.get(item)
        return getattr(self._obj, item, None)

    def __contains__(self, item):
        """ Checks if a Describe object has the specified property. """
        if isinstance(self._obj, dict):
            return item in self._obj
        return hasattr(self._obj, item)

    def __bool__(self):
        """ Checks if the Describe object is 'truthy' (i.e. not ``None``). """
        if self._obj:
            return True
        return False

    def get(self, key: str, default: _tp.Any = None) -> _tp.Any:
        """
        Returns the property value of a Describe object item, returning *default* when not found.

        :param key:     The name of the property.
        :param default: The default value to return in case the property was not found.
        """
        if isinstance(self._obj, dict):
            return self._obj.get(key, default)
        return getattr(self._obj, key, default)

    @property
    def error(self) -> _tp.Union[Exception, None]:
        """
        If the Describe failed because of an error, this will return the error instance (or ``None`` otherwise).
        """
        return self._error

    def num_rows(self, where_clause=None) -> int:
        """
        Returns the number of rows in the table or feature class.

        If the described object does not support this action or does not have any rows, 0 will be returned.

        :param where_clause:    An optional where clause to base the row count on.
        :type where_clause:     str, geocom.tools.queries.Where
        """
        if where_clause:
            if isinstance(where_clause, str):
                field = _tu.unquote(where_clause.split()[0])
            elif hasattr(where_clause, 'fields'):
                field = where_clause.fields[0]
            else:
                raise ValueError('where_clause must be a string or Where instance')

            # Iterate over the dataset rows, using the (first) field from the where_clause
            with _cursors.SearchCursor(self.catalogPath, field, where_clause=where_clause) as rows:
                num_rows = sum(1 for _ in rows)
            del rows

        else:
            # Use the ArcPy GetCount() tool for the row count
            num_rows = int(_arcpy.GetCount_management(self.catalogPath).getOutput(0))

        return num_rows

    def fields(self, names_only: bool = False, uppercase: bool = False) -> _tp.List[_tp.Union[str, _arcpy.Field]]:
        """
        Returns a list of all fields in the described object (if any).

        :param names_only:  When ``True`` (default=``False``),
                            a list of field names instead of ``Field`` instances is returned.
        :param uppercase:   When ``True`` (default=``False``), the returned field names will be uppercase.
                            This also applies when *names_only* is set to return ``Field`` instances.
        :return:            List of field names or ``Field`` instances.
        """
        if _ATTR_FIELDS not in self:
            return []
        fields = [field.name if names_only else field for field in self._obj.fields]
        if uppercase:
            if names_only:
                return [field.upper() for field in fields]
            else:
                for f in fields:
                    f.name = f.name.upper()
        return fields

    def editable_fields(self, names_only: bool = False,
                        uppercase: bool = False) -> _tp.List[_tp.Union[str, _arcpy.Field]]:
        """
        For data elements that have a *fields* property (e.g. Feature classes, Tables and workspaces),
        this will return a list of all editable (writable) fields.

        :param names_only:  When ``True`` (default=``False``),
                            a list of field names instead of ``Field`` instances is returned.
        :param uppercase:   When ``True`` (default=``False``), the returned field names will be uppercase.
                            This also applies when *names_only* is set to return ``Field`` instances.
        :return:            List of field names or ``Field`` instances.
        """
        return [field.name if names_only else field for field in self.fields(uppercase=uppercase) if field.editable]

    @property
    def special_fields(self) -> SpecialFields:
        """
        Returns a container object with all special/reserved Esri fields (e.g. Shape, ObjectID, Area, etc.).
        """
        return SpecialFields(self)
