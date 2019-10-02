# coding: utf-8

# Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

"""
Module that simplifies working with Esri Geodatabase or workspace paths.
"""

import os
from collections import Counter as _Counter
from warnings import warn as _warn

import geocom.common.paths as _paths
import geocom.common.textutils as _tu
import geocom.common.validate as _vld
from geocom.tools import arcpy as _arcpy

ESRI_EXT_SDE = '.sde'
ESRI_EXT_FGDB = '.gdb'
ESRI_EXT_MDB = '.mdb'
ESRI_EXT_ACCDB = '.accdb'

ESRI_GDB_EXTENSIONS = (
    ESRI_EXT_SDE,
    ESRI_EXT_FGDB,
    ESRI_EXT_MDB,
    ESRI_EXT_ACCDB
)

_ARG_SEP = 'separator'
_ARG_QF = 'qualifier'


def is_gdbpath(path: str) -> bool:
    """
    Checks if the given path could be an Esri Geodatabase path by searching for 1 (and only 1!) of its known extensions.
    Note however that this does not truly guarantee that the path actually refers to a geodatabase!

    :param path:    The path to verify.
    """
    path = _paths.get_abs(path).lower()
    hits = 0
    for ext in ESRI_GDB_EXTENSIONS:
        hits += path.count(ext)
    return hits == 1


def split_gdbpath(path: str, remove_qualifier: bool = True) -> tuple:
    """
    Splits the Esri Geodatabase *path* into a ``tuple`` of *(workspace, feature_dataset, feature_class/table)*.
    If any of the output tuple parts is not present, these will be set to an empty string.
    Note that if the path refers to a table or feature class that is not stored in a feature dataset,
    the *feature_dataset* part in the output tuple will be an empty string and the last part will contain the table
    or feature class name.

    Examples:

        >>> split_gdbpath('C:/test.gdb/table')
        ('C:\\test.gdb', '', 'table')
        >>> split_gdbpath('C:/test.sde/qualifier.featureclass', False)
        ('C:\\test.sde', '', 'qualifier.featureclass')
        >>> split_gdbpath('C:/test.sde/qualifier.fds/qualifier.fc')
        ('C:\\test.sde', 'fds', 'fc')

    :param path:                The full path to the Geodatabase feature class or table.
    :param remove_qualifier:    If ``True``, the split parts are "unqualified". If any DB qualifiers exist in the path,
                                they will be removed. This is the default behaviour.
                                Set this parameter to ``False`` if qualifiers must be persisted.
    :raises ValueError:         If the given path does not seem to be a Geodatabase path or
                                there are more than 2 levels in the Geodatabase.
    """
    _vld.pass_if(is_gdbpath(path), ValueError, '{} does not seem to be a valid Esri Geodatabase path'.format(path))
    path = _paths.normalize(path, False)
    path_parts = path.split('\\')
    num_parts = len(path_parts)

    # Find the part that contains the GDB extension
    endpos = 1
    for endpos, p in enumerate(path_parts):
        if p.lower().endswith(ESRI_GDB_EXTENSIONS):
            break
    startpos = endpos + 1

    # Set the workspace path and return it if the path isn't any longer than that
    ws_path = '\\'.join(path_parts[:startpos])
    if num_parts == startpos:
        return ws_path, _tu.EMPTY_STR, _tu.EMPTY_STR

    # If there are more than 2 levels (i.e. feature dataset and feature class), raise an error
    _vld.raise_if(num_parts > startpos + 2, ValueError, 'Geodatabase path cannot be more than 2 levels deep')

    last_parts = [(unqualify(p) if remove_qualifier else p) for p in path_parts[startpos:]]
    if len(last_parts) == 2:
        # If the path is 2 elements deep, output all as-is
        return tuple([ws_path] + last_parts)
    else:
        # Detect if the input path was a feature dataset or not and output accordingly
        try:
            meta = _arcpy.Describe(path)
            if not meta.dataType == 'FeatureDataset':
                raise ValueError
        except (RuntimeError, IOError, AttributeError, ValueError, NameError):
            return ws_path, _tu.EMPTY_STR, last_parts[0]
        return ws_path, last_parts[0], _tu.EMPTY_STR


def exists(path: str) -> bool:
    """
    Returns True if *path* exists. Esri paths (e.g. feature classes) are also supported.

    This function can be slightly faster than Esri's :func:`Exists`, because it checks first if the *workspace* path
    exists using Python's built-in ``os.path`` module. If this is not the case, it immediately returns ``False``.
    Only if the workspace exists, it will use Esri's :func:`Exists` to check the complete path.

    :param path:    The path to verify.
    """
    root = WorkspaceManager.get_root(path)
    if not os.path.exists(root):
        return False
    return _arcpy.Exists(path)


def unqualify(element: str) -> str:
    """
    Removes the qualifier (and anything before that) for a data element part.
    """
    return element.split(_tu.DOT)[-1]


class WorkspaceManager(_paths.BasePathManager):
    """
    WorkspaceManager(workspace, {qualifier=''}, {root=None}, {separator='.'})

    Helper class to generate fully qualified paths for elements (tables, feature datasets etc.) in an Esri workspace.
    An Esri Workspace can be anything ranging from an SDE connection file to a File Geodatabase folder or a simple
    directory containing Shapefiles.

    Please note that the specified *workspace* is never explicitly checked for existence.
    If the user wants to validate the path, use the :func:`exists`, :func:`is_file` or :func:`is_dir` properties.
    An exception to the rule is the :func:`find_path` function, which will validate the path before it is returned.

    If you like to return the *WorkspaceManager* as its normalized initial path (e.g. for printing purposes),
    simply wrap it into a ``str`` statement.
    Note that the *WorkspaceManager* also be used as a context manager using the ``with`` statement.

    :param workspace:   The workspace path (e.g. File Geodatabase, SDE connection file) or name.
    :param qualifier:   An optional database qualifier. If not set and *workspace* is a remote database,
                        the qualifier will be equal to the DB user specified in the SDE connection file.
    :param base:        When this is set to a directory path, the *WorkspaceManager* assumes
                        that *workspace* is relative to this *base* directory and will make *workspace* absolute.
                        Otherwise, it will leave *workspace* unchanged (whether absolute or relative).
    :keyword separator: Optional separator (default = ``'.'``) between the qualifier and the data element name.
    :type separator:    str
    :raises ValueError: If *qualifier* has not been set and the workspace is an existing remote database
                        for which the properties cannot be retrieved, initialization will fail.
    """

    def __init__(self, workspace: str, qualifier: str = _tu.EMPTY_STR, base: str = None, **kwargs):
        super().__init__(workspace, base)
        self._is_remote = self.get_root(self._path.lower()).endswith(ESRI_EXT_SDE)
        self._sep = kwargs.get(_ARG_SEP, _tu.DOT)
        self._qualifier = self._get_qualifier(qualifier)
        self._fds_lookup = {}

    def _get_qualifier(self, qualifier=_tu.EMPTY_STR):
        # Makes sure the qualifier (when specified) ends with a separator and returns it.

        if not self._is_remote or qualifier is None:
            # If it's an SDE/remote workspace (regardless of qualifier),
            # or when the qualifier is None, set it to an empty string.
            qualifier = _tu.EMPTY_STR
        if not qualifier and self._is_remote:
            try:
                # For Oracle databases, the user name is the qualifier. We could derive that from the connection
                # properties by doing a Describe() on the workspace. However, for other databases (e.g. MSSQL), this is
                # not so straight-forward. Moreover, Describe() tends to be quite slow on a whole workspace.
                # For this reason, we will iterate over a bunch of object names in the workspace (starting with
                # Feature Datasets - and when not found, Feature Classes and Tables) to try and fetch the most common
                # qualifier prefix.
                with _arcpy.EnvManager(workspace=self._path):
                    items = _arcpy.ListDatasets() or _arcpy.ListFeatureClasses() or _arcpy.ListTables()
                    qkeys = (self._sep.join(item.split(self._sep)[:-1]) for item in items)
                    qualifier, _ = _Counter(qkeys).most_common()[0]
            except (AttributeError, IOError, RuntimeError):
                raise ValueError('{} could not determine qualifier '
                                 'from SDE connection file'.format(WorkspaceManager.__name__))

        return self._fix_qualifier(qualifier, self._sep)

    def _map_fc(self, lookup, *parts):
        """ Maps a feature dataset to a feature class for lookup purposes. """
        if len(parts) != 2:
            return
        ds, fc = parts
        fc_key = unqualify(fc.lower())
        fc_values = lookup.setdefault(fc_key, [])
        fc_values.append(self.qualify(ds))

    def _map_fds(self):
        """ Creates a complete lookup for all dataset-based feature classes in the root workspace. """
        fds_lookup = {}
        try:
            with _arcpy.EnvManager(workspace=self.get_root(self._path)):
                ds_list = _arcpy.ListDatasets(feature_type='Feature') or []
                for ds in ds_list:
                    fc_list = _arcpy.ListFeatureClasses(feature_dataset=ds) or []
                    for fc in fc_list:
                        self._map_fc(fds_lookup, ds, fc)
        except (RuntimeError, AttributeError) as e:
            _warn('Failed to create Feature Dataset lookup: {}'.format(e))
        return fds_lookup

    def _make_path(self, qualifier, separator, *parts):
        # Builds a complete (qualified) path for the given inputs.
        return _paths.join(self._path, *(self.qualify(p, qualifier, separator) for p in parts if p))

    @staticmethod
    def _fix_qualifier(qualifier=_tu.EMPTY_STR, separator=_tu.DOT):
        # Appends the separator (.) to the qualifier if it is missing (and if there is a qualifier).
        if qualifier and not qualifier.endswith(separator):
            qualifier += separator
        return qualifier

    @staticmethod
    def _is_gdb_root(path):
        # Returns True if path ends with an Esri geodatabase extension.
        return path.lower().endswith(ESRI_GDB_EXTENSIONS)

    @classmethod
    def get_parent(cls, path: str, outside_gdb: bool = False) -> str:
        """
        Class method that extracts the parent workspace path for a given Esri table/feature class path.
        Depending on the path, this might return a feature dataset workspace or the root workspace path.

        :param path:        Full path to an Esri table, feature class or feature dataset.
        :param outside_gdb: If ``True``, this will allow the function to return the parent directory
                            of a Geodatabase, if the workspace is a GDB path. This effectively means that the function
                            is allowed to go 'outside' of the Geodatabase.
                            By default, this value is set to ``False``.
                            For non-Geodatabase paths, this will have no effect: the parent directory is returned.

        Examples:

            >>> WorkspaceManager.get_parent(r'C:/temp/test.gdb')
            'C:\\temp\\test.gdb'
            >>> WorkspaceManager.get_parent(r'C:/temp/test.gdb/feature_dataset')
            'C:\\temp\\test.gdb'
            >>> WorkspaceManager.get_parent(r'C:/temp/test.gdb', outside_gdb=True)
            'C:\\temp'
            >>> WorkspaceManager.get_parent(r'C:/temp/test.shp')
            'C:\\temp'
        """
        parent_dir = os.path.normpath(os.path.dirname(path))
        if outside_gdb or not is_gdbpath(path):
            return parent_dir
        return os.path.normpath(path) if cls._is_gdb_root(path) else parent_dir

    @classmethod
    def get_root(cls, path: str) -> str:
        """
        Class method that extracts the root workspace for a given Esri table/feature class path.

        A root workspace is the Esri workspace of the "highest order". For an SDE feature class, this is the SDE
        connection file, for a File Geodatabase table, this is the File Geodatabase directory (.gdb) itself.
        For a Shapefile path, this will return the parent directory.

        :param path:    Full path to an Esri table, feature class or feature dataset.

        Examples:

            >>> WorkspaceManager.get_root(r'C:/temp/test.gdb/ele/ele_kabel')
            'C:\\temp\\test.gdb'
            >>> WorkspaceManager.get_root(r'C:/temp/mydir/test.shp')
            'C:\\temp\\mydir
            >>> WorkspaceManager.get_root(r'C:/temp/test.gdb/ele')
            'C:\\temp\\test.gdb'

        """
        parent = cls.get_parent(path)
        if not is_gdbpath(path):
            # return `parent` if `path` is not a GDB path (e.g. for Shapefiles)
            return parent

        if cls._is_gdb_root(parent):
            # return `parent` if it is the DB root workspace
            return os.path.normpath(parent)

        # return parent of `parent` if `parent` is not the DB root workspace
        return cls.get_parent(parent)

    @property
    def is_remote(self) -> bool:
        """
        Returns ``True`` if the workspace path seems to be a remote SDE geodatabase connection.
        """
        return self._is_remote

    @property
    def is_gdb(self) -> bool:
        """
        Returns ``True`` if the workspace path seems to be an Esri Geodatabase (remote or local).
        """
        return is_gdbpath(self._path)

    @property
    def root(self) -> 'WorkspaceManager':
        """
        Returns the root workspace as a new ``WorkspaceManager`` instance.
        If the initial path already was the root path, this will return the current instance (``self``).
        """
        root = self.get_root(self._path)
        if root == self._path:
            return self
        return WorkspaceManager(root, self._qualifier, separator=self._sep)

    @property
    def parent(self) -> 'WorkspaceManager':
        """
        Returns the parent workspace as a new ``WorkspaceManager`` instance.
        """
        parent = self.get_parent(self._path)
        return WorkspaceManager(parent, self._qualifier, separator=self._sep)

    @property
    def exists(self) -> bool:
        """
        Returns ``True`` if the workspace path exists and/or is a valid Esri workspace.
        """
        return exists(self._path) if self.is_gdb else os.path.exists(self._path)

    @property
    def qualifier(self) -> str:
        """
        Returns the qualifier for the current Esri workspace. For local workspaces, this is an empty string.
        The trailing separator will not be included in the output string.
        """
        return self._qualifier.rstrip(self._sep)

    @property
    def separator(self) -> str:
        """
        Returns the separator for the current Esri workspace. For local workspaces, this is an empty string.
        """
        return self._qualifier[-1:]

    def qualify(self, name: str, qualifier: str = None, separator: str = None) -> str:
        """
        Qualifies (prefixes) a data element name for SDE workspaces.
        If the workspace is not an SDE workspace or the name is qualified already, the input name is returned as-is.

        :param name:        Feature dataset, feature class or table name.
        :param qualifier:   Optional qualifier if the one derived from the DB connection should be overridden.
        :param separator:   Optional separator if the initial one should be overridden (defaults to ``'.'``).
        :raises ValueError: If no table name was specified.
        """
        _vld.pass_if(name, ValueError, 'qualify() requires a table name')
        if not self._qualifier or self._sep in name:
            # return immediately when name seems to contain a qualifier or workspace is local (i.e. not qualified)
            return name

        # make sure that the name does not start with a qualifier already
        name = unqualify(name)

        if qualifier:
            # use the qualifier override instead of self._qualifier
            return self._fix_qualifier(qualifier, separator or self._sep) + name

        # return the name with the default self._qualifier
        return self._qualifier + name

    def find_path(self, table: str, refresh: bool = False) -> str:
        """
        Tries to resolve the full (qualified) path for the specified table or feature class and returns it,
        by looking up the matching feature dataset (or workspace root when not found).
        In contrast to the :func:`construct` function, the path is verified before it is returned.

        :param table:       The (unqualified) table or feature class name to find.
        :param refresh:     Updates the internal table lookup first. See note below.
        :raises ValueError: If the table was not found or found multiple times (should not happen).

        Example:

            >>> wm = WorkspaceManager(r'C:/temp/db_user.sde')
            >>> wm.qualifier
            'user'
            >>> wm.find_path('ele_cable')  # finds the feature class in feature dataset "ELE"
            'C:\\temp\\db_user.sde\\user.ele\\user.ele_cable'

        .. note::           The feature dataset lookup is created once on the first call to this function.
                            This means that the first call is relatively slow and consecutive ones are fast.
                            When the user creates new feature class paths using the :func:`construct` method,
                            the lookup is updated automatically, so that this function can find the new feature class.
                            However, when the workspace is updated *from the outside*, the lookup is not updated.
                            If the user wishes to force-update the lookup, set the *refresh* argument to ``True``.
        """
        if refresh or not self._fds_lookup:
            self._fds_lookup = self._map_fds()

        table_name = unqualify(table)
        fds = self._fds_lookup.get(table_name.lower(), (_tu.EMPTY_STR,))
        if len(fds) > 1:
            # This case is rare, but it could happen (e.g. when qualifiers are different, but table name matches)
            raise ValueError('{} could belong to {}'.format(_tu.to_repr(table_name), _tu.format_iterable(fds, _tu.OR)))

        qualifier = self._sep.join(fds[0].split(self._sep)[:-1])
        path = self._make_path(qualifier, self._sep, fds[0], table_name)
        if not _arcpy.Exists(path):
            raise ValueError('{} was not found at {}'.format(_tu.to_repr(table_name), path))
        return path

    def construct(self, *parts: str, **kwargs) -> str:
        """
        construct(*parts, {qualifier}, {separator})

        Constructs a (qualified) path for the given named parts (data elements) in the order they appear.

        :param parts:           Feature dataset, feature class and/or table name(s) to concatenate.
                                Note that if the workspace is a FileSystem directory, the last part of `parts` should
                                include a file extension (e.g. '.shp').
        :keyword qualifier:     Optional qualifier if the one derived from the DB connection should be overridden.
        :keyword separator:     Optional separator if the initial one should be overridden (defaults to '.').
        :raises IndexError:     When more than 2 `parts` have been specified, this function will fail.

        In the following example, the qualifier ("user") is derived from the connection:

            >>> wm = WorkspaceManager(r'C:/temp/db_user.sde')
            >>> wm.qualifier
            'user'
            >>> wm.construct('ele', 'ele_kabel')
            'C:\\temp\\db_user.sde\\user.ele\\user.ele_kabel'

        Using the ``WorkspaceManager`` above, we can override the qualifier with a custom one:

            >>> wm.construct('ele', 'ele_kabel', qualifier='editor')
            'C:\\temp\\db_user.sde\\editor.ele\\editor.ele_kabel'

        """
        _vld.raise_if(len(parts) > 2, IndexError,
                      "{}.construct() cannot be called with more than 2 'parts' arguments".
                      format(WorkspaceManager.__name__))

        qualifier = kwargs.get(_ARG_QF, self._qualifier)
        separator = kwargs.get(_ARG_SEP, self._sep)
        self._map_fc(self._fds_lookup, *parts)  # update the lookup, if necessary
        return self._make_path(qualifier, separator, *parts)

    def __eq__(self, other):
        return isinstance(other, WorkspaceManager) and str(self) == str(other)


def get_workspace(table_path: str, root: bool = False, **kwargs) -> WorkspaceManager:
    """
    Extracts the workspace from *table_path* and returns a :class:`WorkspaceManager` instance for it.
    By default (``root=False``), this will return the first workspace it can find in an upwards direction:
    i.e. for a feature class inside a feature dataset, the feature dataset path will be returned.

    :param table_path:  The full path to a table or feature class.
    :param root:        If ``True`` (default = ``False``), the root workspace will be extracted.
    :param kwargs:      Optional keyword arguments for the :class:`WorkspaceManager` initialization.

    Examples:

        >>> get_workspace(r'C:/temp/test.gdb/feature_dataset/feature_class')
        WorkspaceManager('C:\\temp\\test.gdb\\feature_dataset')
        >>> get_workspace(r'C:/temp/test.gdb/feature_dataset/feature_class', root=True)
        WorkspaceManager('C:\\temp\\test.gdb')
    """
    if root:
        path = WorkspaceManager.get_root(table_path)
    else:
        path = WorkspaceManager.get_parent(table_path)
    return WorkspaceManager(path, **kwargs)
