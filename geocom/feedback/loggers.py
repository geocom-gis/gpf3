# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

"""
This module provides a standardized alternative to the built-in Python Logger (``logging`` package).
"""

import atexit as _ae
import logging as _logging
import sys
import typing as _tp
from datetime import datetime as _dt

import more_itertools as _iter

import geocom.common.textutils as _tu
import geocom.common.validate as _vld
import geocom.feedback.formatters as _fmt
import geocom.feedback.handlers as _hndlr

_LOGLINE_LENGTH = 80
_LOGLVL_CRITICAL = 'FATAL'
_LOGLVL_WARNING = 'WARN'

LOG_DEBUG = _logging.DEBUG
LOG_INFO = _logging.INFO
LOG_WARN = _logging.WARNING
LOG_ERROR = _logging.ERROR


class Logger(object):
    """
    Logger(identity, {log_file}, {level}, {encoding}, {time_tag}, {logname_len})

    Standard logger class that logs to stdout (e.g. console) and optionally a file.

    :param identity:        The name of the owner of this Logger, as it will appear in the log file entries.
    :param log_file:        The name or path to the output log file. If no log file is required, leave it empty.
                            When this is omitted, the Logger will only write to the standard stream (e.g. console).
                            If there's already a log handler for this file, this handler will be used automatically.
    :param level:           The minimum log level of messages that should be logged. Defaults to INFO.
    :keyword logname_len:   The maximum length of the logger name used in the log record. Defaults to 15.
    :keyword encoding:      The encoding to use in log **files**. Defaults to the preferred system encoding.
    :keyword time_tag:      When set to ``True`` (default), a timestamp will be appended to the log file name.
    :type encoding:         str
    :type time_tag:         bool
    :type logname_len:      int

    .. note::               For more information about valid *log_file* values, please refer to
                            the *filename* argument for :class:`geocom.feedback.handlers.FileLogHandler`.
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

        # Add custom log level names (if not added already)
        _logging.addLevelName(_logging.CRITICAL, _LOGLVL_CRITICAL)
        _logging.addLevelName(_logging.WARNING, _LOGLVL_WARNING)

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
            handler.setFormatter(_fmt.StreamFormatter())
        return handler

    def _get_filehandler(self):
        """ Returns a matching FileLogHandler for the current Logger instance. """
        return self._get_handler(lambda h: isinstance(h, _hndlr.FileLogHandler) and h.identity == self._fileid)

    def _attach_filehandler(self):
        """ Hooks up a new FileLogHandler for the current Logger instance. """
        handler = _hndlr.FileLogHandler(self._fileid, **self._options)
        handler.setFormatter(_fmt.FileLogFormatter(**self._options))
        handler.addFilter(_logging.Filter(self._name))
        return handler

    def _set_filehandler(self, logger):
        """ If a log file was specified, attach an existing or new file handler for it. """
        if not self._fileid:
            return
        logger.addHandler(self._get_filehandler() or self._attach_filehandler())

    def _close_handlers(self):
        """ Closes all handlers and clears the log handler list. """
        for h in self._log.handlers:
            if hasattr(h, 'close'):
                h.close()
            elif hasattr(h, 'flush'):
                h.flush()
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
            self._log.warning("Suppressed logging exception. {}".format(err))

    @property
    def file_path(self) -> (str, None):
        """ Returns the (first) file path of the current Logger (if setup as file-based logger). """
        fh = self._get_filehandler()
        if fh:
            return fh.baseFilename
        return None

    def info(self, message: str, *args, **kwargs):
        """
        Writes an info/standard message.

        :param message: The text to write.
        :param args:    Optional values for `message` placeholders.
        :param kwargs:  Optional arguments (e.g. `exc_info=True` for exception stack trace logging).
        """
        self._process_msg(LOG_INFO, message, *args, **kwargs)

    def warn(self, message: str, *args, **kwargs):
        """
        Writes a warning message and increments the warning counter. Multi-line messages count as 1 warning.

        :param message: The text to write.
        :param args:    Optional values for `message` placeholders.
        :param kwargs:  Optional arguments (e.g. `exc_info=True` for exception stack trace logging).
        """
        self._process_msg(LOG_WARN, message, *args, **kwargs)
        self._num_warn += 1

    def error(self, message: str, *args, **kwargs):
        """
        Writes an error message and increments the error counter. Multi-line messages count as 1 error.

        :param message: The text to write.
        :param args:    Optional values for `message` placeholders.
        :param kwargs:  Optional arguments (e.g. `exc_info=True` for exception stack trace logging).
        """
        self._process_msg(LOG_ERROR, message, *args, **kwargs)
        self._num_err += 1

    def fatal(self, message: str, *args, **kwargs):
        """
        Writes a fatal error message and increments the error counter. Multi-line messages count as 1 error.

        :param message: The text to write.
        :param args:    Optional values for `message` placeholders.
        :param kwargs:  Optional arguments (e.g. `exc_info=True` for exception stack trace logging).
        """
        self._process_msg(_logging.FATAL, message, *args, **kwargs)
        self._num_err += 1

    def exception(self, message: str, *args, **kwargs):
        """
        Writes a fatal error message and increments the error counter. Multi-line messages count as 1 error.

        :param message: The text to write.
        :param args:    Optional values for `message` placeholders.
        """
        if self._log:
            self._log.exception(message, *args, **kwargs)
        else:
            print(message)
        self._num_err += 1

    def section(self, message: str = _tu.EMPTY_STR, max_length: int = 80, symbol: str = _tu.DASH):
        """
        Writes a centered message wrapped inside a section line to the log.
        When message exceeds *max_length*, it will be logged as-is.
        The actual length of the line will be *max_length* - length of logger name.

        :param message:         The text to put in the middle of the line (optional).
        :param max_length:      The maximum length of the line.
        :param symbol:          The character to generate the line.
        """
        max_length -= len(self._log.name)
        msg_length = len(message)
        if msg_length < max_length - 2:
            fill_char = _tu.SPACE   # default separator between line and message
            if msg_length == 0:
                fill_char = symbol  # separator if there is no message
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
            >>> l.warn('message')
            WARNING: message
            >>> l.status()
            Logged 1 error and 1 warning.
            >>> l.reset_stats()
            >>> l.status()
            Logged 0 errors and 0 warnings.

        """
        errors = _tu.format_plural('error', self._num_err)
        warnings = _tu.format_plural('warning', self._num_warn)
        self.info('Logged {} and {}.', errors, warnings)

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
            self.info('%s() executed in %s', func.__name__, _tu.format_timedelta(start))
        else:
            self.info('Time elapsed: %s', _tu.format_timedelta(self._tstart))

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

    def quit(self, error_msg: str = None):
        """
        Releases the current logger and shuts down the (main) logger.

        :param error_msg:     Optional termination message (or code) for fatal errors.
        """
        if error_msg:
            self.exception(error_msg)
        self._close_handlers()
        self._log = None


class ArcLogger(Logger):
    """
    ArcLogger(identity, {log_file}, {level}, {encoding},

    Logger that forwards all messages to ArcGIS and optionally logs to a file.
    Forwarding messages to ArcGIS is only useful when logging from an ArcToolbox or GEONIS Python script.

    :param identity:        The name of the owner of this Logger, as it will appear in the log file entries.
    :param log_file:        The name or path to the output log file. If no log file is required, leave it empty.
                            If there's already a log handler for this file, this handler will be used automatically.
    :param level:           The minimum log level of messages that should be logged. Defaults to INFO.
    :keyword encoding:      The encoding to use in log files (only). Defaults to Latin-1 a.k.a. cp1252.
    :keyword time_tag:      When set to True (default), a timestamp will be appended to the log file name.
    :keyword logname_len:   The maximum length of the logger name used in the log record. Defaults to 15.
    """

    def __init__(self, identity: str, log_file=None, level: int = LOG_INFO, **options):
        super().__init__(identity, log_file, level, **options)

    def _get_streamhandler(self):
        """ Returns an existing ArcLogHandler or StreamHandler or a new one when not found. """
        handler = self._get_handler(lambda h: isinstance(h, _hndlr.ArcLogHandler))
        if not handler:
            handler = _hndlr.ArcLogHandler(sys.stdout)
            handler.setFormatter(_fmt.StreamFormatter())
        return handler
