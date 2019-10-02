# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

"""
Module that simplifies working with file or directory paths.
"""

import inspect as _inspect
import os

import geocom.common.textutils as _tu
import geocom.common.validate as _vld

_ARG_SEP = 'separator'
_ARG_QF = 'qualifier'


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
    head, tail = os.path.split(os.path.normpath(path))
    name, ext = os.path.splitext(tail)
    return head, name, ext


def normalize(path: str, casefold: bool = True) -> str:
    """
    Normalizes a path and turns it into lowercase, unless *lowercase* is set to ``False``.

    :param path:        The path to normalize.
    :param casefold:    If ``True`` (default), the path will be made case-insensitive (lowercase).
                        If ``False``, the case remains unchanged.
    """
    norm_path = os.path.normpath(path)
    return norm_path.casefold() if casefold else norm_path


def join(*args: str) -> str:
    """
    Joins one or more paths together to create a complete path and normalizes it.

    :param args:    One or more paths/parts.
    """
    return os.path.normpath(os.path.join(*args))


def get_abs(path: str, base: str = None) -> str:
    """
    Creates a normalized absolute path based on *path* relative to *base*. If *base* is not specified,
    the base will be the directory to the file path of the calling function, i.e. when a script 'test.py' calls
    make_absolute(), the directory which contains 'test.py' will be the base.

    :param path:        The relative path to turn into an absolute one.
    :param base:        The base path that serves as the 'root' of the relative path.
    :raises ValueError: If the *base* path is ``None`` and no valid base directory was found using the caller path.
    """
    if os.path.isabs(path):
        return os.path.normpath(path)
    if not base:
        # Get the base path by looking at the which function called this one.
        # The caller frame should be the second frame (1) in the stack.
        # This returns a tuple of which the first value (0) is the frame object.
        frame = _inspect.stack()[1][0]
        base = os.path.dirname(_inspect.getfile(frame))
        if not os.path.isdir(base):
            raise ValueError('Failed to determine base path from caller')
    return join(base, path)


class BasePathManager(object):
    """
    Base helper class for path management.

    For documentation, please refer to the :class:`PathManager` and
    :class:`geocom.tools.workspace.WorkspaceManager` implementations.
    """

    def __init__(self, path, base=None):
        _vld.pass_if(_vld.is_text(path, False), TypeError, "Attribute 'path' should be a non-empty string")
        self._path = os.path.normpath(path)

        if base:
            _vld.raise_if(os.path.isabs(self._path), ValueError,
                          '{} expects a relative path when root has been set'.format(self.__class__.__name__))
            self._path = get_abs(self._path, base)

        self._head, self._tail = os.path.split(self._path)
        self._end, self._ext = os.path.splitext(self._tail)

    @property
    def exists(self) -> bool:
        """
        Returns ``True`` if the initial path exists (regardless of whether path is a file or directory).
        """
        return os.path.exists(self._path)

    @property
    def is_file(self) -> bool:
        """
        Returns ``True`` if the initial path is an existing file.
        """
        return os.path.isfile(self._path)

    @property
    def is_dir(self) -> bool:
        """
        Returns ``True`` if the initial path is an existing directory.
        """
        return os.path.isdir(self._path)

    def extension(self, keep_dot: bool = True) -> str:
        """
        Returns the extension part of the initial path.
        For directories or files without extension, an empty string is returned.

        :param keep_dot:    When ``False``, the extension's trailing dot will be removed. Defaults to ``True``.
        """
        return self._ext if keep_dot else self._ext.lstrip(_tu.DOT)

    def basename(self, keep_ext: bool = True) -> str:
        """
        Returns a file name (if initial path is a file) or a directory name.

        :param keep_ext:    For files, setting this to ``False`` will remove the file extension. Defaults to ``True``.
                            Note that for directories, this might not have any effect.
        """
        return self._tail if keep_ext else self._end

    def construct(self, *parts: str) -> str:
        """
        Constructs a new path based on the initial path from one or more parts (directories, file names).
        If the initial part seems to be a file path (i.e. when an extension is present),
        the constructed path will be based on the containing directory of this file.

        :param parts:   One or more directory names and/or a file name.

        Examples:

            >>> with PathManager(r'C:/temp') as pm:
            >>>     pm.construct('folder', 'subfolder', 'myfile.txt')
            'C:\\temp\\folder\\subfolder\\myfile.txt'
            >>> with PathManager(r'C:/temp/dummy.txt') as pm:
            >>>     pm.construct('folder', 'subfolder', 'myfile.txt')
            'C:\\temp\\folder\\subfolder\\myfile.txt'

        """
        parts = (self._head,) + parts + (self._tail,) if self._ext else (self._path,) + parts
        return join(*parts)

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


class PathManager(BasePathManager):
    """
    PathManager(path, {base})

    Class that helps to extract the different parts of a file or directory path, or that helps construct new ones based
    upon an input path. Can also be used as a context manager using the ``with`` statement.

    Note that *path* and *root* are never explicitly checked for existence.
    If the user wants to validate these paths, use the :func:`exists`, :func:`is_file` or :func:`is_dir` properties.

    :param path:    The file or directory path on which to operate.
    :param base:    When set to a directory path, the ``PathManager`` assumes
                    that *path* is relative to this *base* directory and will make *path* absolute.
                    Otherwise, it will leave *path* unchanged (whether absolute or relative).

    .. note::       For Python 3, the built-in ``pathlib`` module is recommended over the *PathManager*.
    """

    def __init__(self, path: str, base: str = None):
        super().__init__(path, base)

    def from_extension(self, extension: str, force: bool = False) -> str:
        """
        Returns the initial path with an alternative file *extension*.
        If the initial path did not have an extension (e.g. when it is a directory),
        this function will return the initial unmodified path instead (and have no effect), unless *force* is ``True``.

        :param extension:   New file extension (with or without trailing dot).
        :param force:       When ``True``, the extension will always be appended,
                            even if the initial path is a directory. The default is ``False``.

        Examples:

            >>> with PathManager(r'C:/temp/myfile.txt') as pm:
            >>>     pm.from_extension('log')
            C:\\temp\\myfile.log
            >>> with PathManager(r'C:/temp/mydir') as pm:
            >>>     pm.from_extension('log')
            C:\\temp\\mydir
            >>>     pm.from_extension('gdb', force=True)
            C:\\temp\\mydir.gdb

        """
        if not (self._ext and force):
            return self._path
        sep = _tu.EMPTY_STR if extension.startswith(_tu.DOT) else _tu.DOT
        return join(self._head, '{}{}{}'.format(self.basename(False), sep, extension))

    def from_basename(self, basename: str) -> str:
        """
        Returns the initial path with an alternative basename. This will work for both directories and files.

        :param basename:    The new basename. If basename contains an extension and the initial path is a file path
                            that also had an extension, both the name and extension will be changed.
                            If the initial path is a directory path,
                            the directory name will simply be replaced by the basename.

        Examples:

            >>> with PathManager(r'C:/temp/myfile.txt') as pm:
            >>>     pm.from_basename('newfile')
            C:\\temp\\newfile.txt
            >>>     pm.from_basename('newfile.log')
            C:\\temp\\newfile.log

        """
        base, ext = os.path.splitext(basename)
        return join(self._head, '{}{}'.format(base, ext or self.extension()))
