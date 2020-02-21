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
Module that simplifies working with file or directory paths or Esri workspaces (i.e. Geodatabases).
"""

import inspect as _inspect
import os as _os
from collections import Counter as _Counter
from warnings import warn as _warn

import gpf.common.const as _const
import gpf.common.textutils as _tu
import gpf.common.validate as _vld
from gpf import arcpy as _arcpy

ESRI_GDB_EXTENSIONS = (
    _const.EXT_ESRI_SDE,
    _const.EXT_ESRI_GDB,
    _const.EXT_ESRI_MDB,
    _const.EXT_ESRI_ADB
)

_ARG_SEP = 'separator'
_ARG_QF = 'qualifier'

IN_MEMORY_WORKSPACE = 'in_memory'


def explode(path: str) -> tuple:
    """
    Splits *path* into a ``tuple`` of *(directory, name, extension)*.
    Depending on the input path, *extension* might be an empty string.

    :param path:    The path that should be split.

    Examples:

        >>> explode(r'C:/temp/test.gdb')
        ('C:\\temp', 'test', '.gdb')
        >>> explode(r'C:/temp/folder')
        ('C:\\temp', 'folder', '')
    """
    _vld.pass_if(isinstance(path, str), TypeError, 'Path attribute must be a string')

    head, tail = _os.path.split(_os.path.normpath(path))
    name, ext = _os.path.splitext(tail)
    return head, name, ext


def normalize(path: str, lowercase: bool = True) -> str:
    """
    Normalizes a path and turns it into lowercase, unless *lowercase* is set to ``False``.

    :param path:        The path to normalize.
    :param lowercase:   If ``True`` (default), the path will be turned into lowercase.
                        If ``False``, the case remains unchanged.
    """
    _vld.pass_if(isinstance(path, str), TypeError, 'Path attribute must be a string')

    norm_path = _os.path.normpath(path)
    return norm_path.lower() if lowercase else norm_path


def concat(*args: str) -> str:
    """
    Joins (concatenates) one or more paths together to create a complete path and normalizes it.

    :param args:    One or more paths/parts.
    """
    _vld.pass_if(args and all(isinstance(a, str) for a in args), TypeError, 'All arguments must be strings')

    return normalize(_os.path.join(*args), False)


def get_abs(path: str, base: str = None) -> str:
    """
    Creates a normalized absolute path based on *path* relative to *base*. If *base* is not specified,
    the base will be the directory to the file path of the calling function, i.e. when a script 'test.py' calls
    make_absolute(), the directory which contains 'test.py' will be the base.

    :param path:        The relative path to turn into an absolute one.
    :param base:        The base path that serves as the 'root' of the relative path.
    :raises ValueError: If the *base* path is ``None`` and no valid base directory was found using the caller path.
    """
    if _os.path.isabs(path):
        return normalize(path, False)
    if not base:
        # Get the base path by looking at the function that called get_abs().
        # The caller frame should be the second frame (1) in the stack.
        # This returns a tuple of which the first value (0) is the frame object.
        # Note: that path returned by inspect.getabsfile() is lower case!
        frame = _inspect.stack()[1][0]
        base = _os.path.dirname(_inspect.getabsfile(frame))
        if not _os.path.isdir(base):
            raise ValueError('Failed to determine base path from caller')
    return concat(base, path)


def find_parent(path: str, name: str) -> str:
    """
    Finds within *path* the parent directory that contains a file or directory with the given *name*.
    Note that *path* and *name* values are matched case-insensitively, but the found path is returned
    in the original case (as a normalized path).

    If no matches have been found or if the match has no parent, an empty string is returned.
    If there are multiple matches, the parent path of the first match is returned.

    Examples:

        >>> find_parent('C:\\Projects\\parent\\LEVEL0\\level1\\level2.txt', 'level0')
        'C:\\Projects\\parent'
        >>> find_parent('C:\\Projects\\parent\\LEVEL\\level\\level.txt', 'level')
        'C:\\Projects\\parent'
        >>> find_parent('C:\\Projects\\some_dir', 'C:')
        ''
        >>> find_parent('C:\\Projects\\parent\\must_include_extension.txt', 'must_include_extension')
        ''

    :param path:    The path to search.
    :param name:    The name for which to search the parent directory in *path*.
                    This value can be a file name (with extension!) or a directory name.
                    Partial paths, pre- or suffixes or regular expressions are not allowed here and will return None.
    """

    def match_parts(plist, n):
        # Search for n in plist and yield the parts up to n
        n_ci = n.lower()
        if n_ci not in (p.lower() for p in plist):
            return

        for p in plist:
            if p.lower() == n_ci:
                return
            yield p

    # Validate arguments
    _vld.pass_if(isinstance(name, str), TypeError, 'name attribute must be a string')

    # Split path into parts list, encode or decode name if name type does not match path type
    parts = normalize(path, False).split(_os.sep)

    # Return the concatenated path parts up til the match (or an empty string if nothing was found)
    return _os.sep.join(match_parts(parts, name)) or _const.CHAR_EMPTY


class Path(object):
    """
    Path(path, {base})

    The ``Path`` class helps to extract the different parts of a file or directory path, or helps make_path new ones
    based upon a root path. This class can also be used as a context manager using the ``with`` statement.

    Note that *path* (and *base*) are never explicitly checked for existence.
    If the user wishes to validate these paths, use the :func:`exists`, :func:`is_file` or :func:`is_dir` properties.

    **Params:**

    -   **path** (str, unicode):

        The file or directory path on which to operate.

    -   **base** (str, unicode):

        When set to a directory path, the ``Path`` class assumes that *path* is relative
        to this *base* directory and will make *path* absolute.
        Otherwise, it will leave *path* unchanged (whether absolute or relative).

    .. seealso::    For Esri Geodatabase paths, use the :class:`gpf.paths.Workspace` class.
    """

    def __init__(self, path, base=None):
        _vld.pass_if(_vld.is_text(path, False), TypeError, "Attribute 'path' should be a non-empty string")
        self._path = _os.path.normpath(path)

        if base:
            _vld.raise_if(_os.path.isabs(self._path), ValueError,
                          f'{self.__class__.__name__} expects a relative path when root has been set')
            self._path = get_abs(self._path, base)

        self._head, self._tail = _os.path.split(self._path)
        self._end, self._ext = _os.path.splitext(self._tail)

    @property
    def exists(self) -> bool:
        """
        Returns ``True`` if the initial path exists (regardless of whether path is a file or directory).
        """
        return _os.path.exists(self._path)

    @property
    def is_file(self) -> bool:
        """
        Returns ``True`` if the initial path is an existing file.
        """
        return _os.path.isfile(self._path)

    @property
    def is_dir(self) -> bool:
        """
        Returns ``True`` if the initial path is an existing directory.
        """
        return _os.path.isdir(self._path)

    def extension(self, keep_dot: bool = True) -> str:
        """
        Returns the extension part of the initial path.
        For directories or files without extension, an empty string is returned.

        :param keep_dot:    When ``False``, the extension's trailing dot will be removed. Defaults to ``True``.
        """
        return self._ext if keep_dot else self._ext.lstrip(_const.CHAR_DOT)

    def basename(self, keep_ext: bool = True) -> str:
        """
        Returns a file name (if initial path is a file) or a directory name.

        :param keep_ext:    For files, setting this to ``False`` will remove the file extension. Defaults to ``True``.
                            Note that for directories, this might not have any effect.
        """
        return self._tail if keep_ext else self._end

    def from_extension(self, extension: str, force: bool = False):
        """
        Returns the initial path with an alternative file *extension*.
        If the initial path did not have an extension (e.g. when it is a directory),
        this function will return the initial unmodified path instead (and have no effect), unless *force* is ``True``.

        :param extension:   New file extension (with or without trailing dot).
        :param force:       When ``True``, the extension will always be appended,
                            even if the initial path is a directory. The default is ``False``.

        Examples:

            >>> with Path(r'C:/temp/myfile.txt') as pm:
            >>>     pm.from_extension('log')
            C:\\temp\\myfile.log
            >>> with Path(r'C:/temp/mydir') as pm:
            >>>     pm.from_extension('log')
            C:\\temp\\mydir
            >>>     pm.from_extension('gdb', force=True)
            C:\\temp\\mydir.gdb

        """
        if not (self._ext and force):
            return self._path
        sep = _const.CHAR_EMPTY if extension.startswith(_const.CHAR_DOT) else _const.CHAR_DOT
        return concat(self._head, f'{self.basename(False)}{sep}{extension}')

    def from_basename(self, basename: str) -> str:
        """
        Returns the initial path with an alternative basename. This will work for both directories and files.

        :param basename:    The new basename. If basename contains an extension and the initial path is a file path
                            that also had an extension, both the name and extension will be changed.
                            If the initial path is a directory path,
                            the directory name will simply be replaced by the basename.

        Examples:

            >>> with Path(r'C:/temp/myfile.txt') as pm:
            >>>     pm.from_basename('newfile')
            C:\\temp\\newfile.txt
            >>>     pm.from_basename('newfile.log')
            C:\\temp\\newfile.log

        """
        base, ext = _os.path.splitext(basename)
        return concat(self._head, '{}{}'.format(base, ext or self.extension()))

    def make_path(self, *parts):
        """
        Constructs a new path based on the initial path from one or more parts (directories, file names).
        If the initial part seems to be a file path (i.e. when an extension is present),
        the constructed path will be based on the containing directory of this file.

        :param parts:   One or more directory names and/or a file name.
        :rtype:         str, unicode

        Examples:

            >>> with Path(r'C:/temp') as pm:
            >>>     pm.make_path('folder', 'subfolder', 'myfile.txt')
            'C:\\temp\\folder\\subfolder\\myfile.txt'
            >>> with Path(r'C:/temp/dummy.txt') as pm:
            >>>     pm.make_path('folder', 'subfolder', 'myfile.txt')
            'C:\\temp\\folder\\subfolder\\myfile.txt'

        """
        parts = (self._head,) + parts + (self._tail,) if self._ext else (self._path,) + parts
        return concat(*parts)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def __repr__(self):
        """ Returns the representation of this instance. """
        return '{}({!r})'.format(self.__class__.__name__, self._path)

    def __str__(self):
        """ Returns the normalized initial path. """
        return self._path


def is_gdbpath(path: str) -> bool:
    """
    Checks if the given path could be an Esri Geodatabase path by searching for 1 (and only 1!) of its known extensions.
    Note however that this does not truly guarantee that the path actually refers to a geodatabase!

    :param path:    The path to verify.
    """
    if path.casefold() == IN_MEMORY_WORKSPACE:
        return True
    path = get_abs(path).lower()
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
    _vld.pass_if(is_gdbpath(path), ValueError, f'{path} does not seem to be a valid Esri Geodatabase path')
    path = normalize(path, False)
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
        return ws_path, _const.CHAR_EMPTY, _const.CHAR_EMPTY

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
            return ws_path, _const.CHAR_EMPTY, last_parts[0]
        return ws_path, last_parts[0], _const.CHAR_EMPTY


def exists(path: str) -> bool:
    """
    Returns True if *path* exists. Esri paths (e.g. feature classes) are also supported.

    This function can be slightly faster than Esri's :func:`Exists`, because it checks first if the *workspace* path
    exists using Python's built-in ``os.path`` module. If this is not the case, it immediately returns ``False``.
    Only if the workspace exists, it will use Esri's :func:`Exists` to check the complete path.

    :param path:    The path to verify.
    """
    root = Workspace.get_root(path)
    if not _os.path.exists(root):
        return False
    return _arcpy.Exists(path)


def unqualify(element: str) -> str:
    """
    Removes the qualifier (and anything before that) for a data element part.
    """

    name = _os.path.basename(element)
    if _const.CHAR_DOT in name:
        return name.split(_const.CHAR_DOT)[-1]
    return name


class Workspace(Path):
    """
    Workspace({path='in_memory', {qualifier=''}, {base=None}, {separator='.'})

    Helper class to generate fully qualified paths for elements (tables, feature datasets etc.) in an Esri workspace.
    An Esri Workspace can be anything ranging from an SDE connection file to a File Geodatabase folder or a simple
    directory containing Shapefiles.

    **If ``Workspace`` is initialized without parameters, an in-memory workspace is assumed.**

    Please note that the specified *workspace* is never explicitly checked for existence.
    If the user wants to validate the path, use the :func:`exists`, :func:`is_file` or :func:`is_dir` properties.
    An exception to the rule is the :func:`find_path` function, which will validate the path before it is returned.

    If you like to return the workspace as its normalized initial path (e.g. for printing purposes),
    simply call :func:`str` on the ``Workspace`` instance.
    Note that the ``Workspace`` class can also behave like a context manager using the ``with`` statement.

    **Params:**

    -   **path** (str, unicode):

        The workspace path (e.g. File Geodatabase, SDE connection file) or name.
        Leave empty if you wish to use an in-memory workspace.

    -   **qualifier** (str, unicode):

        An optional database qualifier. If not set and *workspace* is a remote database,
        the qualifier will be equal to the DB user specified in the SDE connection file.

    -   **base** (str, unicode):

        When set to a directory path, the ``Workspace`` class assumes that *path* is relative
        to this *base* directory and will make *path* absolute.
        Otherwise, it will leave *path* unchanged (whether absolute or relative).

    **Keyword params:**

    -   **separator** (str, unicode):

        Optional separator (default = ``'.'``) between the qualifier and the data element name.

    :raises ValueError: If *qualifier* has not been set and the workspace is an existing remote database
                        for which the properties cannot be retrieved, initialization will fail.
    """

    def __init__(self, path=IN_MEMORY_WORKSPACE, qualifier=_const.CHAR_EMPTY, base=None, **kwargs):
        super().__init__(path, base)
        self._is_remote = self.get_root(self._path.lower()).endswith(_const.EXT_ESRI_SDE)
        self._sep = kwargs.get(_ARG_SEP, _const.CHAR_DOT)
        self._qualifier = self._get_qualifier(qualifier)
        self._fds_lookup = {}

    def _get_qualifier(self, qualifier: str = _const.CHAR_EMPTY) -> str:
        # Makes sure the qualifier (when specified) ends with a separator and returns it.

        if not self._is_remote or qualifier is None:
            # If it's an SDE/remote workspace (regardless of qualifier),
            # or when the qualifier is None, set it to an empty string.
            qualifier = _const.CHAR_EMPTY
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
                raise ValueError(f'{Workspace.__name__} could not determine qualifier from SDE connection file')

        return self._fix_qualifier(qualifier, self._sep)

    def _map_fc(self, lookup: dict, *parts):
        """ Maps a feature dataset to a feature class for lookup purposes. """
        if len(parts) != 2:
            return
        ds, fc = parts
        if not ds:
            # Feature class (or table) is not inside a dataset: no need to map
            return
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
            _warn(f'Failed to create Feature Dataset lookup: {e}')
        return fds_lookup

    def _make_path(self, qualifier, separator, *parts):
        # Builds a complete (qualified) path for the given inputs.
        return concat(self._path, *(self.qualify(p, qualifier, separator) for p in parts if p))

    @staticmethod
    def _fix_qualifier(qualifier: str = _const.CHAR_EMPTY, separator: str = _const.CHAR_DOT):
        # Appends the separator (.) to the qualifier if it is missing (and if there is a qualifier).
        if qualifier and not qualifier.endswith(separator):
            qualifier += separator
        return qualifier

    @staticmethod
    def _is_gdb_root(path):
        # Returns True if path ends with an Esri geodatabase extension or if path is in-memory.
        return path.lower().endswith(ESRI_GDB_EXTENSIONS) or path.lower() == IN_MEMORY_WORKSPACE

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

            >>> Workspace.get_parent(r'C:/temp/test.gdb')
            'C:\\temp\\test.gdb'
            >>> Workspace.get_parent(r'C:/temp/test.gdb/feature_dataset')
            'C:\\temp\\test.gdb'
            >>> Workspace.get_parent(r'C:/temp/test.gdb', outside_gdb=True)
            'C:\\temp'
            >>> Workspace.get_parent(r'C:/temp/test.shp')
            'C:\\temp'
        """
        if path.lower() == IN_MEMORY_WORKSPACE:
            return path
        parent_dir = _os.path.normpath(_os.path.dirname(path))
        if outside_gdb or not is_gdbpath(path):
            return parent_dir
        return _os.path.normpath(path) if cls._is_gdb_root(path) else parent_dir

    @classmethod
    def get_root(cls, path: str) -> str:
        """
        Class method that extracts the root workspace for a given Esri table/feature class path.

        A root workspace is the Esri workspace of the "highest order".
        For an SDE feature class, this is the SDE connection file.
        For a File Geodatabase table, this is the File Geodatabase directory (.gdb) itself.
        For a Shapefile path, this will return the parent directory.
        For an in memory workspace, this will return 'in_memory'.

        :param path:    Full path to an Esri table, feature class or feature dataset.

        Examples:

            >>> Workspace.get_root(r'C:/temp/test.gdb/ele/ele_kabel')
            'C:\\temp\\test.gdb'
            >>> Workspace.get_root(r'C:/temp/mydir/test.shp')
            'C:\\temp\\mydir
            >>> Workspace.get_root(r'C:/temp/test.gdb/ele')
            'C:\\temp\\test.gdb'

        """
        parent = cls.get_parent(path)
        if not is_gdbpath(path):
            # return `parent` if `path` is not a GDB path (e.g. for Shapefiles)
            return parent

        if cls._is_gdb_root(parent):
            # return `parent` if it is the DB root workspace
            return _os.path.normpath(parent)

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
    def root(self) -> 'Workspace':
        """
        Returns the root workspace as a new ``Workspace`` instance.
        If the initial path already was the root path, this will return the current instance (``self``).
        """
        root = self.get_root(self._path)
        if root == self._path:
            return self
        return Workspace(root, self._qualifier, separator=self._sep)

    @property
    def parent(self) -> 'Workspace':
        """
        Returns the parent workspace as a new ``Workspace`` instance.
        """
        parent = self.get_parent(self._path)
        return Workspace(parent, self._qualifier, separator=self._sep)

    @property
    def exists(self) -> bool:
        """
        Returns ``True`` if the workspace path exists and/or is a valid Esri workspace.
        """
        return exists(self._path) if self.is_gdb else _os.path.exists(self._path)

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
        In contrast to the :func:`make_path` function, the path is verified before it is returned.

        :param table:       The (unqualified) table or feature class name to find.
        :param refresh:     Updates the internal table lookup first. See note below.
        :raises ValueError: If the table was not found or found multiple times (should not happen).

        Example:

            >>> wm = Workspace(r'C:/temp/db_user.sde')
            >>> wm.qualifier
            'user'
            >>> wm.find_path('ele_cable')  # finds the feature class in feature dataset "ELE"
            'C:\\temp\\db_user.sde\\user.ele\\user.ele_cable'

        .. note::           The feature dataset lookup is created once on the first call to this function.
                            This means that the first call is relatively slow and consecutive ones are fast.
                            When the user creates new feature class paths using the :func:`make_path` method,
                            the lookup is updated automatically, so that this function can find the new feature class.
                            However, when the workspace is updated *from the outside*, the lookup is not updated.
                            If the user wishes to force-update the lookup, set the *refresh* argument to ``True``.
        """
        if refresh or not self._fds_lookup:
            self._fds_lookup = self._map_fds()

        table_name = unqualify(table)
        fds = self._fds_lookup.get(table_name.casefold(), (_const.CHAR_EMPTY,))
        if len(fds) > 1:
            # This case is rare, but it could happen (e.g. when qualifiers are different, but table name matches)
            raise ValueError(f'{_tu.to_repr(table_name)} could belong to {_tu.format_iterable(fds, _const.TEXT_OR)}')

        qualifier = self._sep.join(fds[0].split(self._sep)[:-1])
        path = self._make_path(qualifier, self._sep, fds[0], table_name)
        if not _arcpy.Exists(path):
            raise ValueError(f'{_tu.to_repr(table_name)} was not found at {path}')
        return path

    def make_path(self, *parts: str, **kwargs) -> str:
        """
        make_path(*parts, {qualifier}, {separator})

        Constructs a (qualified) path for the given named parts (data elements) in the order they appear.

        :param parts:           Feature dataset, feature class and/or table name(s) to concatenate.
                                Note that if the workspace is a FileSystem directory, the last part of `parts` should
                                include a file extension (e.g. '.shp').
        :keyword qualifier:     Optional qualifier if the one derived from the DB connection should be overridden.
        :keyword separator:     Optional separator if the initial one should be overridden (defaults to '.').
        :raises IndexError:     When more than 2 `parts` have been specified, this function will fail.

        In the following example, the qualifier ("user") is derived from the connection:

            >>> wm = Workspace(r'C:/temp/db_user.sde')
            >>> wm.qualifier
            'user'
            >>> wm.make_path('ele', 'ele_kabel')
            'C:\\temp\\db_user.sde\\user.ele\\user.ele_kabel'

        Using the ``Workspace`` above, we can override the qualifier with a custom one:

            >>> wm.make_path('ele', 'ele_kabel', qualifier='editor')
            'C:\\temp\\db_user.sde\\editor.ele\\editor.ele_kabel'

        """
        _vld.raise_if(len(parts) > 2, IndexError,
                      f"{Workspace.__name__}.make_path() cannot be called with more than 2 'parts' arguments")

        qualifier = kwargs.get(_ARG_QF, self._qualifier)
        separator = kwargs.get(_ARG_SEP, self._sep)
        self._map_fc(self._fds_lookup, *parts)  # update the lookup, if necessary
        return self._make_path(qualifier, separator, *parts)

    def __eq__(self, other):
        return isinstance(other, Workspace) and str(self) == str(other)


def get_workspace(table_path: str, root: bool = False, **kwargs) -> Workspace:
    """
    Extracts the workspace from *table_path* and returns a :class:`Workspace` instance for it.
    By default (``root=False``), this will return the first workspace it can find in an upwards direction:
    i.e. for a feature class inside a feature dataset, the feature dataset path will be returned.

    :param table_path:  The full path to a table or feature class.
    :param root:        If ``True`` (default = ``False``), the root workspace will be extracted.
    :param kwargs:      Optional keyword arguments for the :class:`Workspace` initialization.

    Examples:

        >>> get_workspace(r'C:/temp/test.gdb/feature_dataset/feature_class')
        Workspace('C:\\temp\\test.gdb\\feature_dataset')
        >>> get_workspace(r'C:/temp/test.gdb/feature_dataset/feature_class', root=True)
        Workspace('C:\\temp\\test.gdb')
    """
    if root:
        path = Workspace.get_root(table_path)
    else:
        path = Workspace.get_parent(table_path)
    return Workspace(path, **kwargs)
