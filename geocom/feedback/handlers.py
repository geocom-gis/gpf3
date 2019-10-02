# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

"""
This module contains Handlers for the ArcLogger and Logger classes.
"""

import logging as _logging
import os as _os
import tempfile as _tf
from datetime import datetime as _dt
from logging import handlers as _handlers

import geocom.common.textutils as _tu
from geocom.tools import arcpy as _arcpy

_LOG_STD_EXT = '.log'
_LOG_ALT_EXT = '.txt'


class FileLogHandler(_handlers.RotatingFileHandler):
    """
    Custom file handler that inherits from ``RotatingFileHandler``.

    By default, the preferred system encoding is used (often set to CP1252 or UTF-8).

    When a :class:`geocom.feedback.loggers.Logger` or :class:`geocom.feedback.loggers.ArcLogger` is set up with this
    file handler, new logger instances (e.g. in other modules or script) will use the same file handler if
    these loggers are initialized using the same *filename*.

    :param filename:    Log file name or absolute or relative path to the log file.
                        If *filename* does not have an extension, a *.log* extension will be added.
                        If *filename* has an extension that does not equal *.txt* or *.log*, it will be set to *.log*.
                        If *time_tag* is ``True`` (default), a *_YYMMDD_HHMMSS* timestamp (current local time)
                        will be added to the log file name automatically.
                        If *filename* is just a name, the output directory will be set to the user temp directory.
                        If *filename* is a relative path, it will be made absolute (relative to ``os.curdir``).
                        If *filename* is an absolute path, that path will be used as-is.
                        If the log directory of *filename* does not exist, it will be created.
    :param time_tag:    If set to ``True`` (default), a _YYMMDD_HHMMSS timestamp will be appended to *filename*.
                        When set to ``False``, *filename* will not receive a timestamp.
    :param encoding:    The optional encoding to use for the output file. Defaults to the preferred system encoding.
    :type filename:     str
    :type time_tag:     bool
    :type encoding:     str

    .. warning::        The user must have write access to the specified output directory.
    """

    def __init__(self, filename, time_tag=True, encoding=_tu.DEFAULT_ENCODING):
        self._id, name = self._get_id_name(filename, time_tag)
        self._make_dir(name)
        super().__init__(name, encoding=encoding)

    @staticmethod
    def _get_id_name(filename, time_tag=True) -> tuple:
        """
        Returns a tuple with (file name/identity, file path) for the *filename* that was used to initialize
        the ``FileLogHandler``. By default, a timestamp will be added to *filename*.
        """
        name, ext = _os.path.splitext(filename)
        if ext.lower() not in (_LOG_STD_EXT, _LOG_ALT_EXT):
            ext = _LOG_STD_EXT
        out_name = (name + _dt.now().strftime('_%Y%m%d_%H%M%S') + ext) if time_tag else (name + ext)
        if not _os.path.isabs(out_name) and not _os.path.normpath(out_name).startswith(('..\\', '.\\')):
            # If the filename is not a relative path or just a name, prepend out_name with a temp directory path
            out_name = _os.path.join(_tf.gettempdir(), out_name)
        return filename, _os.path.realpath(out_name)

    @staticmethod
    def _make_dir(filename):
        """
        Creates the directory for the log file if it doesn't exist.
        Note that this could fail if the user does not have write/execute access.
        """
        dirname = _os.path.dirname(filename)
        if not _os.path.isdir(dirname):
            _os.makedirs(dirname)

    @property
    def identity(self) -> str:
        """
        Returns the "identity" of the ``FileLogHandler``, which is the name or path that was used to instantiate it.

        Note that this often does not equal the path which the ``FileLogHandler`` is actually writing to.
        """
        return self._id


class ArcLogHandler(_logging.StreamHandler):
    """
    Custom log handler that writes to the standard stream (e.g. console) when the log level >= _logging.DEBUG.
    The handler also sends messages to ArcGIS when the log level >= _logging.INFO.
    """

    def __init__(self, stream=None):
        super().__init__(stream)

    @property
    def _func_map(self):
        return {
            _logging.WARN:     _arcpy.AddWarning,
            _logging.WARNING:  _arcpy.AddWarning,
            _logging.ERROR:    _arcpy.AddError,
            _logging.FATAL:    _arcpy.AddError,
            _logging.CRITICAL: _arcpy.AddError,
            _logging.INFO:     _arcpy.AddMessage
        }

    def emit(self, record):
        """
        Emit a record.
        Override of the original StreamHandler.emit() -> see _logging.StreamHandler for documentation.
        Writes messages to ArcGIS for all log levels defined in __FUNC_MAP.
        Writes to stderr when the log level has been set to DEBUG.
        """

        # noinspection PyBroadException
        try:
            msg = self.format(record)
            level = record.levelno
            arc_func = self._func_map.get(level)
            debug_mode = level == _logging.DEBUG

            if debug_mode:
                # Only write to stderr when the message has a DEBUG log level
                super().emit(record)

            if arc_func:
                # Log to ArcGIS if the appropriate log function was found (note: ArcGIS logs to stderr as well)
                arc_func(msg)

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)
