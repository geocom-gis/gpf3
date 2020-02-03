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
This module provides a standardized alternative to the built-in Python Logger (``logging`` package).
"""

import atexit as _ae
import errno as _errno
import logging as _logging
import os as _os
import sys
import tempfile as _tf
import typing as _tp
from logging import handlers as _handlers

import more_itertools as _iter
from datetime import datetime as _dt

import gpf.common.const as _const
import gpf.common.textutils as _tu
import gpf.common.validate as _vld
from gpf import arcpy as _arcpy

_LOGLINE_LENGTH = 80
_LOGNAME_LENGTH = 15
_LOG_FMT_LF = '%s\n'      # Default line-endings (i.e. Unix)
_LOG_FMT_CRLF = '%s\r\n'  # Windows line-endings (carriage return)
_LOG_STD_EXT = '.log'
_LOG_ALT_EXT = '.txt'

# Supported log levels
LOG_DEBUG = _logging.DEBUG
LOG_INFO = _logging.INFO
LOG_WARNING = _logging.WARNING
LOG_ERROR = _logging.ERROR
LOG_CRITICAL = _logging.CRITICAL


class _FileLogHandler(_handlers.RotatingFileHandler):
    """
    Custom file handler that inherits from ``RotatingFileHandler``.

    By default, the preferred system encoding is used (often set to CP1252 or UTF-8).

    When a :class:`gpf.loggers.Logger` or :class:`gpf.loggers.ArcLogger` is set up with this
    file handler, new logger instances (e.g. in other modules or script) will use the same file handler if
    these loggers are initialized using the same *filename*.

    :param filename:    Log file name or absolute or relative path to the log file.
                        For more information, look at the :class:`gpf.loggers.Logger` documentation.
    :param time_tag:    If set to ``True``, a _YYMMDD_HHMMSS timestamp will be appended to *filename*.
                        When set to ``False`` (default), *filename* will not receive a timestamp.
    :param encoding:    The optional encoding to use for the output file. Defaults to the preferred system encoding.
    :type filename:     str
    :type time_tag:     bool
    :type encoding:     str

    .. warning::        The user must have write access to the specified output directory.
    """

    def __init__(self, filename, time_tag=False, encoding=_const.ENC_DEFAULT):
        self._id, file_path = self._get_id_name(filename, time_tag)
        super().__init__(file_path, encoding=encoding)

    @staticmethod
    def _get_id_name(filename, time_tag=False) -> tuple:
        """
        Returns a tuple with (file name/identity, file path) for the *filename* that was used to initialize
        the ``_FileLogHandler``. If *time_tag* is True, a timestamp will be added to *filename*.
        """
        name, ext = _os.path.splitext(filename)
        if ext.lower() not in (_LOG_STD_EXT, _LOG_ALT_EXT):
            ext = _LOG_STD_EXT
        out_name = f'{name}{_dt.now().strftime("_%Y%m%d_%H%M%S")}{ext}' if time_tag else f'{name}{ext}'
        if not _os.path.isabs(out_name) and not _os.path.normpath(out_name).startswith(('..\\', '.\\')):
            # If the filename is not a relative path or just a name, prepend out_name with a temp directory path
            out_name = _os.path.join(_tf.gettempdir(), out_name)
        return filename, _os.path.realpath(out_name)

    def _open(self):
        """
        Override of the RotatingFileHandler._open() function.
        Creates the directory for the log file if it doesn't exist without raising the faulty EEXIST error.
        Note that this could fail if the user does not have write/execute access.
        """
        try:
            _os.makedirs(_os.path.dirname(self.baseFilename))
        except OSError as e:
            if e.errno != _errno.EEXIST:
                raise
        return super()._open()

    @property
    def identity(self) -> str:
        """
        Returns the "identity" of the ``_FileLogHandler``, which is the name or path that was used to instantiate it.

        .. warning::    This often does not equal the path to which the ``_FileLogHandler`` is actually writing.
        """
        return self._id


class _ArcLogHandler(_logging.StreamHandler):
    """
    Custom log handler that writes to the standard stream (e.g. console) when the log level >= _logging.DEBUG.
    The handler also sends messages to ArcGIS when the log level >= _logging.INFO.
    """

    def __init__(self, stream=None):
        super().__init__(stream)

    @property
    def _func_map(self):
        return {
            LOG_WARNING:    _arcpy.AddWarning,
            LOG_ERROR:      _arcpy.AddError,
            LOG_CRITICAL:   _arcpy.AddError,
            LOG_INFO:       _arcpy.AddMessage
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

            if level == LOG_DEBUG:
                # Only write to stderr when the message has a DEBUG log level
                super().emit(record)

            if arc_func:
                # Log to ArcGIS if the appropriate log function was found (note: ArcGIS logs to stderr as well)
                arc_func(msg)

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)


class _FileLogFormatter(_logging.Formatter):
    """
    Custom log file formatter used by the :class:`gpf.loggers._FileLogHandler`.

    This formatter returns a record as **[DD.MM.YYYY | HH:mm:SS | level name | log name] message**.

    By default, the length of the *log name* will be limited to 15 characters.
    If this should be changed, the :class`Logger` can be initialized using a different *max_name*.

    :param logname_length:  The maximum length of the log name in the formatted record.
    """

    def __init__(self, logname_length: int = _LOGNAME_LENGTH):
        self._name_max = logname_length
        fmt_l = '[%(asctime)s | %(levelname)-8.8s | %(name)s] %(message)s'
        fmt_d = '%d.%m.%Y | %H:%M:%S'
        super().__init__(fmt_l, fmt_d)

    def format(self, record):
        """ Format the specified record as text. Overrides the built-in logging.Formatter.format(). """
        len_name = len(record.name)
        if len_name > self._name_max:
            # Truncate/abbreviate logger name with '...' if it's too long
            record.name = record.name[:self._name_max - 3].ljust(self._name_max, _const.CHAR_DOT)
        record.name = record.name.ljust(self._name_max)

        return super().format(record)


class _StreamFormatter(_logging.Formatter):
    """
    Custom log stream formatter used by the :class:`gpf.loggers._ArcLogHandler`.

    This formatter only logs a message, prepended by a level name if it's a WARNING (or higher).
    """

    def __init__(self):
        self._fmt_def = '%(message)s'
        self._fmt_lvl = '%(levelname)s: %(message)s'
        super().__init__(self._fmt_def)

    def format(self, record):
        """ Format the specified record as text. Overrides the built-in logging.Formatter.format(). """
        self._fmt = self._fmt_def
        if record.levelno >= LOG_WARNING:
            # only display log level if it's WARNING or higher
            self._fmt = self._fmt_lvl

        return super().format(record)


class Logger(object):
    """
    Logger(identity, {log_file}, {level}, {encoding}, {time_tag}, {max_name})

    Standard logger class that logs to stdout (e.g. console) and optionally a file.

    **Params:**

    -   **identity** (str, unicode):

        The name of the owner of this Logger, as it will appear in the log file entries.

    -   **log_file** (str, unicode, :class:`gpf.paths.Path`):

        Optional log file name or path to the log file.
        If there's already a log handler for this file, this handler will be used automatically.

        - If *log_file* does not have an extension, a *.log* extension will be added.
        - If *log_file* has an extension, but it's not *.txt* or *.log*, it will be reset to *.log*.
        - If *time_tag* is ``True`` (default), a *_YYMMDD_HHMMSS* timestamp (current local time) \
          will be added to the log file name automatically.
        - If *log_file* is just a name, the output directory will be set to the user temp directory.
        - If *log_file* is a relative path, it will be made absolute (relative to ``os.curdir``).
        - If *log_file* is an absolute path, that path will be used as-is.
        - If the log directory of *log_file* does not exist, it will be created.

        When *log_file* is omitted, the Logger will only write to the stdout stream (e.g. console).

    -   **level** (int):

        The minimum log level of messages that should be logged. Defaults to INFO.

    **Keyword params:**

    -   **max_name** (int):

        The maximum length of the logger name used in the log record. Defaults to 15.

    -   **encoding** (str):

        The encoding to use in log **files**. Defaults to the preferred system encoding.

    -   **time_tag** (bool):

        When set to ``True`` (default), a timestamp will be appended to the log file name.
    """

    def __init__(self, identity: str, log_file=None, level: int = LOG_INFO, **options):
        self._log = None
        self._state = False
        self._num_warn = 0
        self._num_err = 0
        self._name = identity
        self._level = level
        self._fileid = log_file
        self._tstart = _dt.now()
        self._options = options
        _ae.register(self.quit)

    def _get_logger(self):
        """ Sets up and returns a basic logger for `identity`. """
        if self._log:
            # Logger exists. Check if (another)
            self._set_filehandler(self._log)
            return self._log

        # Get basic console logger and attach stream handler
        logger = _logging.getLogger(self._name)
        logger.setLevel(self._level)
        logger.addHandler(self._get_streamhandler())

        # If a log file was specified, attach file handler
        if self._fileid:
            logger.addHandler(self._get_filehandler() or self._attach_filehandler())

        return logger

    def _get_handler(self, match_func):
        """ Returns the first handler where ``match_func(handler) is True``. """
        return _iter.first((h for h in self._log.handlers if match_func(h)), None) if self._log else None

    def _get_streamhandler(self):
        """ Returns an existing StreamHandler or a new one when not found. """
        handler = self._get_handler(lambda h: isinstance(h, _logging.StreamHandler))
        if not handler:
            handler = _logging.StreamHandler(sys.stdout)
            handler.setFormatter(_StreamFormatter())
        return handler

    def _get_filehandler(self):
        """ Returns a matching _FileLogHandler for the current Logger instance. """
        return self._get_handler(lambda h: isinstance(h, _FileLogHandler) and h.identity == self._fileid)

    def _attach_filehandler(self):
        """ Hooks up a new _FileLogHandler for the current Logger instance. """
        handler = _FileLogHandler(self._fileid, **self._options)
        handler.setFormatter(_FileLogFormatter(**self._options))
        handler.addFilter(_logging.Filter(self._name))
        return handler

    def _set_filehandler(self, logger):
        """ If a log file was specified, attach an existing or new file handler for it. """
        if not self._fileid:
            return
        logger.addHandler(self._get_filehandler() or self._attach_filehandler())

    def _close_handlers(self):
        """ Closes all handlers and clears the log handler list. """
        if not self._log:
            # Prevent _close_handlers() method from being executed twice (e.g. by user and by atexit call)
            return
        for h in self._log.handlers:
            if hasattr(h, 'close'):
                h.close()
        # Remove handlers
        self._log.handlers = []

    def _process_msg(self, level, message, *args, **kwargs):
        """
        Prepares `message` for writing (optionally replacing placeholder `args`) and writes it to the log
        for a specified `level`.

        :param int level:   Log level (e.g. logging.INFO, logging.ERROR etc.).
        :param message:     Message to write (optionally with %s placeholders).
        :param args:        Optional placeholder arguments.
        :param kwargs:      Other optional arguments (e.g. `exc_info=True` for exception stack trace logging).
        """
        self._log = self._get_logger()
        try:
            if hasattr(message, 'splitlines'):
                for line in message.splitlines():
                    self._log.log(level, line, *args, **kwargs)
            else:
                self._log.log(repr(message), *args, **kwargs)
        except Exception as err:
            # Never fail on logging errors. These also don't count towards the logging stats.
            self._log.warning(f'Suppressed logging exception. {err}')

    @property
    def file_path(self) -> (str, None):
        """ Returns the (first) file path of the current Logger (if setup as file-based logger). """
        fh = self._get_filehandler()
        if fh:
            return fh.baseFilename
        return None

    def info(self, message: str, **kwargs):
        """
        Writes an info/standard message.

        :param message: The text to write.
        :param kwargs:  Optional arguments (e.g. `exc_info=True` for exception stack trace logging).
        """
        self._process_msg(LOG_INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """
        Writes a warning message and increments the warning counter. Multi-line messages count as 1 warning.

        :param message: The text to write.
        :param kwargs:  Optional arguments (e.g. `exc_info=True` for exception stack trace logging).
        """
        self._process_msg(LOG_WARNING, message, **kwargs)
        self._num_warn += 1

    def error(self, message: str, **kwargs):
        """
        Writes an error message and increments the error counter. Multi-line messages count as 1 error.

        :param message: The text to write.
        :param kwargs:  Optional arguments (e.g. `exc_info=True` for exception stack trace logging).
        """
        self._process_msg(LOG_ERROR, message, **kwargs)
        self._num_err += 1

    def critical(self, message: str, **kwargs):
        """
        Writes a critical error message and increments the error counter. Multi-line messages count as 1 error.

        :param message: The text to write.
        :param kwargs:  Optional arguments (e.g. `exc_info=True` for exception stack trace logging).
        """
        self._process_msg(LOG_CRITICAL, message, **kwargs)
        self._num_err += 1

    def exception(self, message: _tp.Union[str, Exception], **kwargs):
        """
        Writes a critical error message and increments the error counter. Multi-line messages count as 1 error.

        :param message: The text to write.
        :param kwargs:  Optional arguments (e.g. `exc_info=True` for exception stack trace logging).
        """
        if self._log:
            self._log.exception(message, **kwargs)
        else:
            # Write to stderr if no logger was initialized
            print(message, file=sys.stderr)
        self._num_err += 1

    def section(self, message: str = _const.CHAR_EMPTY, max_length: int = 80, symbol: str = _const.CHAR_DASH):
        """
        Writes a centered message wrapped inside a section line to the log.
        When message exceeds *max_length*, it will be logged as-is.

        :param message:         The text to put in the middle of the line (optional).
        :param max_length:      The maximum length of the line.
        :param symbol:          The character to generate the line.
        """
        if not self._log:
            self._log = self._get_logger()
        max_length -= len(self._log.name)
        msg_length = len(message)
        if msg_length < max_length - 2:
            fill_char = _const.CHAR_SPACE   # default separator between line and message
            if msg_length == 0:
                fill_char = symbol          # separator if there is no message
            message = message.center(msg_length + 2, fill_char).center(max_length, symbol)
        self.info(message)

    def status(self):
        """
        Writes a (final) status message to the log, telling the user how
        many errors and warnings were logged by this instance.

        Example:

            >>> l = Logger('test')
            >>> l.error('message')
            ERROR: message
            >>> l.warning('message')
            WARNING: message
            >>> l.status()
            Logged 1 error and 1 warning.
            >>> l.reset_stats()
            >>> l.status()
            Logged 0 errors and 0 warnings.

        """
        errors = _tu.format_plural('error', self._num_err)
        warnings = _tu.format_plural('warning', self._num_warn)
        self.info(f'Logged {errors} and {warnings}.')

    def time_elapsed(self, func: _tp.Callable = None, *args, **kwargs):
        """
        Logs a nicely printed message stating how much time has passed.
        If the callable *func* is specified, this function is executed and its execution time is logged.
        If no callable *func* has been given, the elapsed time (since init or last ``reset_stats`` call) is logged.

        :param func:    The optional callable to execute.
        :param args:    Positional arguments for *func*.
        :param kwargs:  Keyword arguments for *func*.
        """
        if func:
            _vld.pass_if(callable(func), TypeError, "'func' attribute must be a callable")
            start = _dt.now()
            func(*args, **kwargs)
            self.info(f'{func.__name__}() executed in {_tu.format_timedelta(start)}')
        else:
            self.info(f'Time elapsed: {_tu.format_timedelta(self._tstart)}')

    def reset_stats(self, time: bool = True):
        """
        Resets the error and warning counters. Optionally, the start time can also be reset.

        :param time:    When ``True`` (default) the start time of the logger will also be reset (to local ``now()``).
        :type time:     bool
        """
        if time:
            self._tstart = _dt.now()
        self._num_warn = 0
        self._num_err = 0

    def quit(self, error_msg: _tp.Union[Exception, str] = None):
        """
        Releases the current logger and shuts down the (main) logger.

        :param error_msg:   Optional termination message (or Exception instance) for fatal errors.

        ..note::            No more logging can take place after this call.
                            Under normal circumstances, the user does not need to call this method, because it is
                            automatically being called once the user application has exited.
        """
        if error_msg:
            if isinstance(error_msg, Exception):
                self.exception(error_msg)
            else:
                self.critical(error_msg)
        self._close_handlers()
        self._log = None


class ArcLogger(Logger):
    """
    ArcLogger(identity, {log_file}, {level}, {encoding}, {time_tag}, {max_name})

    Logger that forwards all messages to ArcGIS and optionally logs to a file.
    Forwarding messages to ArcGIS is only useful when logging from an ArcToolbox or GEONIS Python script.

    **Params:**

    -   **identity** (str, unicode):

        The name of the owner of this Logger, as it will appear in the log file entries.

    -   **log_file** (str, unicode, :class:`gpf.paths.Path`):

        Optional log file name or path to the log file.
        If there's already a log handler for this file, this handler will be used automatically.

        - If *log_file* does not have an extension, a *.log* extension will be added.
        - If *log_file* has an extension, but it's not *.txt* or *.log*, it will be reset to *.log*.
        - If *time_tag* is ``True`` (default = ``False``), a *_YYMMDD_HHMMSS* timestamp (current local time) \
          will be added to the log file name automatically.
        - If *log_file* is just a name, the output directory will be set to the user temp directory.
        - If *log_file* is a relative path, it will be made absolute (relative to ``os.curdir``).
        - If *log_file* is an absolute path, that path will be used as-is.
        - If the log directory of *log_file* does not exist, it will be created.

        When *log_file* is omitted, the Logger will only write to the stdout stream (e.g. console).

    -   **level** (int):

        The minimum log level of messages that should be logged. Defaults to INFO.

    **Keyword params:**

    -   **max_name** (int):

        The maximum length of the logger name used in the log record. Defaults to 15.

    -   **encoding** (str):

        The encoding to use in log files (only). Defaults to cp1252 on Windows.

    -   **time_tag** (bool):

        When set to ``True`` (default = ``False``), a timestamp will be appended to the log file name.
    """

    def __init__(self, identity: str, log_file=None, level: int = LOG_INFO, **options):
        super().__init__(identity, log_file, level, **options)

    def _get_streamhandler(self):
        """ Returns an existing _ArcLogHandler or StreamHandler or a new one when not found. """
        handler = self._get_handler(lambda h: isinstance(h, _ArcLogHandler))
        if not handler:
            handler = _ArcLogHandler(sys.stdout)
            handler.setFormatter(_StreamFormatter())
        return handler
