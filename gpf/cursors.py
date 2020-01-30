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
This module contains fast **and** user-friendly alternatives to Esri's standard cursors.
The SearchCursor, InsertCursor and UpdateCursor listed here inherit from Esri's *Data Access* cursors,
but there are some differences:

    - SearchCursors return :class:`_Row` wrappers and have a :func:`getValue` function, similar to Esri's legacy rows;
    - Insert- and UpdateCursors return :class:`_MutableRow` wrappers that also have a :func:`setValue` function,
      similar to their legacy predecessors;
    - The ported :func:`getValue` function can return a *default* value when the field was not found
      (in the legacy function, it would raise an exception);
    - The cursors *where_clause* argument also accepts a :class:`gpf.tools.queries.Where` instance.

In theory, one should be able to simply replace the legacy Esri cursors (in an old script, for example)
with the ones in this module without too much hassle, since all legacy methods have been ported to the cursors
in this module.
The only thing you might need to replace and verify for compatibility is the initialization of the cursor itself.

Please refer to Esri's documentation on the
`legacy cursors <https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-classes/cursor.htm>`_
for the ported functions and the `Data Access classes
<https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-data-access/what-is-the-data-access-module-.htm>`_
for cursor initialization and function overrides.
"""

import typing as _tp
from functools import wraps as _wraps

import gpf.common.const as _const
import gpf.common.textutils as _tu
import gpf.common.validate as _vld
import gpf.paths as _paths
import gpf.tools.queries as _q
from gpf import arcpy as _arcpy


def _map_fields(fields: _tp.Iterable[str]) -> dict:
    """ Maps a list of field names to their position (index). """
    return {f.upper(): i for i, f in enumerate(fields)}


def _default_tuple(length: int) -> tuple:
    """ Returns a tuple filled with None values. """
    return tuple(None for _ in range(length))


def _default_list(length: int) -> list:
    """ Returns a list filled with None values. """
    return [None for _ in range(length)]


def _disable(func):
    """ Decorator that raises a NotImplementedError for the 'disabled' wrapped function or method. """

    # noinspection PyUnusedLocal
    @_wraps(func)
    def raise_ni(*args, **kwargs):
        func_name = func.__qualname__ if hasattr(func, '__qualname__') else func.__name__
        raise NotImplementedError(f'The {func_name} {func.__class__.__name__} has been disabled')

    return raise_ni


# noinspection PyPep8Naming
class _Row(object):
    """
    _Row(field_map, {default})

    "View Factory" class for backward compatibility to read values from an immutable row using legacy Esri cursor style.

    This class is only intended for use by a ``SearchCursor``.

    :param field_map:   The field map (name, position) to use for the row value lookup.
    :keyword default:   The iterable type (``list`` or ``tuple``) to use as a data container.
    """

    __slots__ = '_fieldmap', '_data', '_repr'

    def __init__(self, field_map: dict, **kwargs):
        self._fieldmap = field_map
        self._data = kwargs.get('default', _default_tuple(len(field_map)))
        self._repr = '([])'

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, item):
        return self._data[item]

    def __repr__(self):
        return self._repr.format(_const.TEXT_COMMASPACE.join(_tu.to_repr(v) for v in self._data))

    def __getslice__(self, i, j):
        return self._data[i:j]

    def __call__(self, row: _tp.Iterable = None):
        self._data = _default_tuple(len(self._fieldmap)) if row is None else row
        return self

    def getValue(self, field: str, default: _tp.Any = _const.OBJ_EMPTY) -> _tp.Any:
        """
        Returns the value that matches the given *field* name for the current row.

        A *default* can be specified in case the value was not found.

        :param field:       The (case-insensitive) name of the field for which to retrieve the value.
        :param default:     The default value to return in case the field was not found.
        :raise ValueError:  If *default* is omitted and a value cannot be found.
        :return:            A value (an Esri or Python basic type) or ``None``.
        """
        try:
            return self[self._fieldmap[field.upper()]]
        except (KeyError, IndexError):
            _vld.raise_if(default is _const.OBJ_EMPTY, ValueError,
                          f'getValue() field {field!r} does not exist and no default value was provided')
            return default

    def isNull(self, field: str) -> bool:
        """
        Returns ``True`` if the *field* value is NULL (``None``) or if *field* does not exist in the current row.

        :param field:   The (case-insensitive) name of the field for which to check its value.
        """
        return self.getValue(field, None) is None

    def asDict(self) -> dict:
        """
        Convenience function to return the current row as a dictionary of ``{field: value}``.
        """
        return {k: self[i] for k, i in self._fieldmap.items()}


# noinspection PyPep8Naming
class _MutableRow(_Row):
    """
    _MutableRow(field_map, {default})

    "View Factory" class for backwards compatibility to fetch values from a mutable row using legacy Esri cursor style.

    This class is only intended for use by an``InsertCursor`` or ``UpdateCursor``.

    :param field_map:   The field map (name, position) to use for the row value lookup.
    """

    def __init__(self, field_map: dict):
        super().__init__(field_map, default=_default_list(len(field_map)))
        self._repr = '[{}]'

    def __call__(self, row: _tp.Iterable = None):
        self._data = _default_list(len(self._fieldmap)) if row is None else row
        return self

    def __setitem__(self, key, value):
        self._data[key] = value

    def setValue(self, field: str, value: _tp.Any) -> None:
        """
        Sets the *field* to *value* for the current row.

        If the *field* was not found, this function does nothing.

        :param field:       The (case-insensitive) name of the field for which to set the value.
        :param value:       The value to set (must be an Esri or Python basic type).
        """
        try:
            self[self._fieldmap[field.upper()]] = value
        except (KeyError, IndexError):
            pass

    def setNull(self, field: str) -> None:
        """
        Sets the specified *field* value to NULL (``None``).

        If the *field* was not found, no action is performed.

        :param field:   The (case-insensitive) name of the field which should be set to NULL.
        """
        self.setValue(field, None)


# noinspection PyPep8Naming, PyUnusedLocal
class Editor(_arcpy.da.Editor):
    """
    Context manager wrapper for Esri's Data Access Editor class that opens an edit session on a workspace.
    This class does not do more than Esri's Editor class, but it tends to be more user-friendly.

    This Editor only has a :func:`start` and :func:`stop` method. The other available methods (:func:`startOperation`,
    :func:`undoOperation` etc.) have been disabled to avoid confusion.

    The recommended way of using the Editor is as a context manager (using the ``with`` statement).
    This has the advantage that, upon failure, the edit session is closed automatically (optionally with rollback).
    If no failures occurred, the edit session is closed normally and all edits are saved (committed).
    However, one can also instantiate the Editor and call :func:`start` and :func:`stop` respectively when done.

    **Params:**

    -   **path** (str, unicode, class:`gpf.paths.Workspace`):

        A path on which to open the edit session. This can be a table or feature class path,
        a workspace path or a class:`gpf.paths.Workspace` instance.

    -   **with_undo** (bool):

        If ``True`` (default = ``False``), an undo stack will be kept.
        For versioned workspaces, this setting has no effect (always ``True``).
        For all other workspaces, having this value set to ``False`` improves performance.

    .. note::           The :class:`InsertCursor` and :class:`UpdateCursor` in this module use the Editor on demand,
                        if these cursors are initialized with the *auto_edit* option set to ``True`` (default).
    .. seealso::        https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-data-access/editor.htm
    """

    def __init__(self, path: _tp.Union[str, _paths.Workspace], with_undo: bool = False):
        if not isinstance(path, _paths.Workspace):
            path = _paths.get_workspace(path, True)
        super().__init__(str(path))
        self._versioned = (len(_arcpy.da.ListVersions(str(path))) > 1) if path.is_remote else False
        # If the database is versioned, always use the undo stack
        self._undo = self._versioned or with_undo

    def __enter__(self):
        self.start(self._undo)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.stop(False)
        else:
            self.stop(True)

    def start(self, with_undo: bool = False) -> None:
        """
        Starts the edit operation.
        If the Editor already is in an editing state, this method will do nothing.

        :param with_undo:   If set to ``True``, the undo/redo stack is enabled.
                            Note that this stack will always be enabled if the workspace is a versioned SDE geodatabase.
        """
        if self.isEditing:
            # If the Editor already is in an editing state, do nothing
            return
        # If the database is versioned, always use the undo stack
        self._undo = self._versioned or with_undo
        super().startEditing(self._undo, self._versioned)
        super().startOperation()

    def stop(self, save: bool = True) -> None:
        """
        Stops the edit operation.
        If the Editor is not in an editing state, this method will do nothing.

        :param save:    If set to ``True``, the edits will be saved.
                        If set to ``False``, the edits will be rolled back (and not saved) when either
                        (a) the edit session was started with an undo/redo stack, or
                        (b) the workspace is a versioned SDE database.
                        If the undo stack was disabled (default) and *save* is ``False``, the operation will be aborted.
        """
        if not self.isEditing:
            # If the Editor is not in an editing state, do nothing
            return
        if save:
            super().stopOperation()
        else:
            if self._undo and self._versioned:
                super().undoOperation()
            else:
                super().abortOperation()
        super().stopEditing(save)

    @_disable
    def startEditing(self, *args): pass
    @_disable
    def stopEditing(self, *args): pass
    @_disable
    def startOperation(self, *args): pass
    @_disable
    def stopOperation(self, *args): pass
    @_disable
    def abortOperation(self, *args): pass
    @_disable
    def undoOperation(self, *args): pass
    @_disable
    def redoOperation(self, *args): pass


class SearchCursor(_arcpy.da.SearchCursor):
    """
    SearchCursor(in_table, {field_names}, {where_clause}, {spatial_reference}, {explode_to_points}, {sql_clause})

    Wrapper class to properly expose ArcPy's Data Access SearchCursor and its methods.
    Returns a read-only cursor to iterate over (a set of) records in a table.

    If *where_clause* is used and it's a :class:`Where` instance (recommended),
    the field delimiters will automatically be resolved (e.g. for Oracle, MS SQL, File Geodatabase etc.).

    **Params:**

    -   **datatable**:

        The path to the feature class or table, or a Layer or table view.

    -   **field_names**:

        Single field name or a sequence of field names.
        When not set, all fields are returned. This is not recommended, as it tends to be slow and consumes more memory.

    -   **where_clause** (str, unicode, :class:`gpf.tools.queries.Where`):

        An optional expression that filters the returned records.

    **Keyword params:**

    -   **spatial_reference** (str, int, arcpy.SpatialReference):

        An optional SpatialReference object or its string representation or WKID equivalent.
        The returned features will be reprojected to this coordinate system on the fly.

    -   **explode_to_points** (bool):

        Optional. If ``True``, features are deconstructed into individual vertices.
        This means that e.g. for a feature with 5 vertices, 5 features will be returned for each vertex.

    -   **sql_clause** (tuple, list):

        An optional sequence of 2 elements, containing a SQL prefix and postfix query respectively.
        These queries support clauses like GROUP BY, DISTINCT, ORDER BY and so on.
        The clauses do not support the use of :class:`gpf.tools.queries.Where` instances.
    """

    def __init__(self, datatable: str, field_names: _tp.Union[str, _tp.Iterable[str], None] = _const.CHAR_ASTERISK,
                 where_clause: _tp.Union[str, _q.Where] = None, **kwargs):
        _q.add_where(kwargs, where_clause, datatable)
        super().__init__(datatable, field_names, **kwargs)
        self._row = _Row(_map_fields(self.fields))

    def __next__(self) -> _Row:
        return self._row(super().__next__())

    @property
    def fields(self) -> _tp.List[str]:
        """
        Returns a list of fields (in order) used by the cursor.
        """
        return super().fields

    def reset(self):
        """ Resets the cursor position to the first row so it can be iterated over again. """
        return super().reset()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return


# noinspection PyPep8Naming
class InsertCursor(_arcpy.da.InsertCursor):
    """
    InsertCursor(in_table, field_names, {auto_edit})

    Wrapper class to properly expose ArcPy's Data Access InsertCursor and its methods.
    Returns a cursor to insert new records into a table.

    **Params:**

    -   **datatable**:

        The path to the feature class or table, or a Layer or table view.

    -   **field_names**:

        Single field name or a sequence of field names.
        When not set, all fields are returned. This is not recommended, as it tends to be slow and consumes more memory.

    **Keyword params:**

    -   **auto_edit** (bool):

        If set to ``True`` (default), an edit session is started automatically, if required.
    """

    def __init__(self, datatable: str, field_names: _tp.Union[str, _tp.Iterable[str]], **kwargs):
        self._editor = None
        try:
            super().__init__(datatable, field_names)
        except RuntimeError as e:
            if 'edit session' in str(e).lower() and kwargs.get('auto_edit', True):
                self._editor = Editor(datatable)
                self._editor.start()
                super().__init__(datatable, field_names)
                return
            raise
        self._field_map = _map_fields(self.fields)

    @property
    def fields(self) -> _tp.List[str]:
        """
        Returns a list of fields (in order) used by the cursor.
        """
        return super().fields

    def newRow(self, values: _tp.Iterable = None) -> _MutableRow:
        """
        Returns a new MutableRow instance (optionally populated with data).

        :param values:      Optional ``list`` or ``tuple`` of field values in the correct ``InsertCursor`` field order
                            or a ``dict`` of key-value pairs, where the keys specify the field names to set.
        :raises ValueError: If *values* is a ``list`` or ``tuple`` and the length does not match the number of
                            cursor fields, or if *values* is a ``dict`` and one of the keys does not match with the
                            cursor field names.
        """

        _vld.raise_if(values and not _vld.is_iterable(values), ValueError,
                      "newRow() 'values' should be iterable or None")

        # Although it would be more efficient to initialize _MutableRow once and simply call it
        # to set its values, this might not be what the user expects. Therefore, we (re)initialize it each time.
        if isinstance(values, dict):
            row = _MutableRow(self._field_map)
            for k, v in values.items():
                row.setValue(k, v)
        else:
            row = _MutableRow(self._field_map)(values)

        return row

    def insertRow(self, row: _tp.Iterable) -> int:
        """
        Inserts a new row.

        :param row: The row values to insert.
        :return:    The ObjectID of the inserted row (when successful).
        """
        return super().insertRow(row)

    def _close(self, save):
        if self._editor:
            self._editor.stop(save)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close(False if exc_type else True)

    def __del__(self):
        self._close(True)


# noinspection PyPep8Naming
class UpdateCursor(_arcpy.da.UpdateCursor):
    """
    UpdateCursor(in_table, {field_names}, {where_clause}, {spatial_reference}, {explode_to_points}, {sql_clause})

    Wrapper class to properly expose ArcPy's Data Access UpdateCursor and its methods.
    Returns a cursor to iterate over and update (a set of) records in a table.

    If *where_clause* is used and it's a :class:`Where` instance, the field delimiters will
    automatically be resolved (e.g. for Oracle, MS SQL, File Geodatabase etc.).

    **Params:**

    -   **datatable**:

        The path to the feature class or table, or a Layer or table view.

    -   **field_names**:

        Single field name or a sequence of field names.
        When not set, all fields are returned. This is not recommended, as it tends to be slow and consumes more memory.

    -   **where_clause** (str, unicode, :class:`gpf.tools.queries.Where`):

        An optional expression that filters the returned records.

    **Keyword params:**

    -   **spatial_reference** (str, int, arcpy.SpatialReference):

        An optional SpatialReference object or its string representation or WKID equivalent.
        The returned features will be reprojected to this coordinate system on the fly.

    -   **explode_to_points** (bool):

        Optional. If ``True``, features are deconstructed into individual vertices.
        This means that e.g. for a feature with 5 vertices, 5 features will be returned for each vertex.

    -   **sql_clause** (tuple, list):

        An optional sequence of 2 elements, containing a SQL prefix and postfix query respectively.
        These queries support clauses like GROUP BY, DISTINCT, ORDER BY and so on.
        The clauses do not support the use of :class:`gpf.tools.queries.Where` instances.

    -   **auto_edit** (bool):

        If set to ``True`` (default), an edit session is started automatically, if required.
    """

    def __init__(self, datatable: str, field_names: _tp.Union[str, _tp.Iterable[str]],
                 where_clause: _tp.Union[str, _q.Where] = None, **kwargs):
        self._editor = None
        _q.add_where(kwargs, where_clause, datatable)
        try:
            super().__init__(datatable, field_names, **kwargs)
        except RuntimeError as e:
            if 'edit session' in str(e).lower() and kwargs.get('auto_edit', True):
                self._editor = Editor(datatable)
                self._editor.start()
                super().__init__(datatable, field_names, **kwargs)
            else:
                raise
        self._row = _MutableRow(_map_fields(self.fields))

    def __next__(self):
        return self._row(super().__next__())

    @property
    def fields(self) -> _tp.List[str]:
        """
        Returns a list of fields (in order) used by the cursor.
        """
        return super().fields

    def reset(self):
        """ Resets the cursor position to the first row so it can be iterated over again. """
        return super().reset()

    # noinspection PyUnusedLocal
    def deleteRow(self, dummy=None) -> int:
        """
        Deletes the current row. The *dummy* argument only serves backwards compatibility and is not used.

        :return:    The ObjectID of the deleted row (when successful).
        """
        return super().deleteRow()

    def updateRow(self, row: _tp.Iterable) -> int:
        """
        Updates the current row.

        :param row: The row values to update.
        :return:    The ObjectID of the updated row (when successful).
        """
        return super().updateRow(row)

    def _close(self, save):
        if self._editor:
            self._editor.stop(save)
            self._editor = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close(False if exc_type else True)

    def __del__(self):
        self._close(True)
