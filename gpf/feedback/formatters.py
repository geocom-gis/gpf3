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
This module contains Formatters for the ArcLogger and Logger classes.
"""

import logging as _logging

import gpf.common.textutils as _tu

_LOGNAME_LENGTH = 15


class FileLogFormatter(_logging.Formatter):
    """
    Custom log file formatter used by the :class:`gpf.feedback.handlers.FileLogHandler`.

    This formatter returns a record as **[DD.MM.YYYY | HH:mm:SS | level name | log name] message**.

    By default, the length of the *log name* will be limited to 15 characters.
    If this should be changed, the Formatter can be initialized using a different *logname_len*.

    :param logname_len: The maximum length of the log name in the formatted record.
    :type logname_len:  int
    """

    def __init__(self, logname_len=_LOGNAME_LENGTH):
        self._name_max = logname_len
        fmt_l = '[%(asctime)s | %(levelname)-5.5s | %(name)s] %(message)s'
        fmt_d = '%d.%m.%Y | %H:%M:%S'
        super().__init__(fmt_l, fmt_d)

    def format(self, record):
        """ Format the specified record as text. Overrides the built-in logging.Formatter.format(). """
        len_name = len(record.name)
        if len_name > self._name_max:
            # Truncate/abbreviate logger name with '...' if it's too long
            record.name = record.name[:self._name_max - 3].ljust(self._name_max, _tu.DOT)
        record.name = record.name.ljust(self._name_max)

        return super().format(record)


class StreamFormatter(_logging.Formatter):
    """
    Custom log stream formatter used by the :class:`gpf.feedback.handlers.ArcLogHandler`.

    This formatter only logs a message, prepended by a level name if it's a WARNING (or higher).
    """

    def __init__(self):
        self._fmt_def = '%(message)s'
        self._fmt_lvl = '%(levelname)s: %(message)s'
        super().__init__(self._fmt_def)

    def format(self, record):
        """ Format the specified record as text. Overrides the built-in logging.Formatter.format(). """
        self._fmt = self._fmt_def
        if record.levelno >= _logging.WARN:
            # only display log level if it's WARN or higher
            self._fmt = self._fmt_lvl
            if record.levelname == _logging.getLevelName(_logging.WARN):
                record.levelname = 'WARNING'

        return super().format(record)
