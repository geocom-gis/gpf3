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
Module that contains helper functions to improve text handling and formatting.
"""

import typing as _tp
from numbers import Number as _Number

from datetime import datetime as _dt

import gpf.common.const as _const
import gpf.common.validate as _vld


def get_alphachars(text: str) -> str:
    """
    Returns all alphabetic characters [a-zA-Z] in string *text* in a new (concatenated) string.

    Example:

        >>> get_alphachars('Test123')
        'Test'

    :param text:    The string to search.
    """
    _vld.pass_if(_vld.is_text(text), TypeError, "'text' attribute must be a string (got {!r})".format(text))
    return _const.CHAR_EMPTY.join(s for s in text if s.isalpha())


def get_digits(text: str) -> str:
    """
    Returns all numeric characters (digits) in string *text* in a new (concatenated) **string**.

    Example:

        >>> get_digits('Test123')
        '123'
        >>> int(get_digits('The answer is 42'))
        42

    :param text:    The string to search.
    """
    _vld.pass_if(_vld.is_text(text), TypeError, "'text' attribute must be a string (got {!r})".format(text))
    return _const.CHAR_EMPTY.join(s for s in text if s.isdigit())


def to_str(value: _tp.Any, encoding: str = _const.ENC_UTF8) -> str:
    """
    This function behaves similar to the built-in :func:`str` method: it converts any value into a string.
    However, if *value* is a ``bytes`` object, it will be decoded according to the specified *encoding*.

    :param value:       The value to convert to string.
    :param encoding:    The encoding to use when value is a ``bytes`` object.

    .. note::           By default, the encoding is UTF-8, unless the user specified something else.
                        If this function fails to decode the value into ``str`` using the specified encoding,
                        the default system encoding is used instead (which often is cp1252).
                        For this fallback case, the 'replace' method is used, which means that it will not
                        raise an error if it fails. Bytes that fail to decode will be replaced by a question mark.
    """
    if isinstance(value, bytes):
        try:
            return value.decode(encoding)
        except UnicodeError:
            return value.decode(_const.ENC_DEFAULT, errors='replace')
    else:
        return str(value)


def to_bytes(value: _tp.Any, encoding: str = _const.ENC_UTF8) -> bytes:
    """
    This function behaves similar to the built-in :func:`bytes` method: it converts any value into a ``bytes`` object.
    However, if *value* is a ``str``, it will be decoded according to the specified *encoding*.

    :param value:       The value to convert to bytes.
    :param encoding:    The encoding to use when value is a ``str``.

    .. note::           By default, the encoding is UTF-8, unless the user specified something else.
                        If this function fails to encode the value into bytes using the specified encoding,
                        the default system encoding is used instead (which often is cp1252).
                        For this fallback case, the 'replace' method is used, which means that it will not
                        raise an error if it fails. Characters that fail to encode will be replaced by a question mark.
    .. warning::        Python 3 only!
    """
    if isinstance(value, str):
        try:
            return value.encode(encoding)
        except UnicodeError:
            return value.encode(_const.ENC_DEFAULT, errors='replace')
    else:
        return bytes(value)


def to_repr(value: _tp.Any, encoding: str = _const.ENC_UTF8) -> str:
    """
    This function behaves similar to the built-in :func:`repr` method: it converts any value into its representation.
    However, if *value* is a bytes-like object, it will be decoded using the specified *encoding* (defaults to UTF-8).
    The encoding will use the 'replace' method, which means that it will not raise an error if it fails.
    This means that the representation of the bytes-like object will not have the 'b' prefix anymore.

    :param value:       The value for which to get its representation.
    :param encoding:    The encoding to use when value is a ``bytes`` or ``bytearray`` object.
    """
    if isinstance(value, (str, bytes, bytearray)):
        return repr(to_str(value, encoding))
    else:
        return repr(value)


def capitalize(text: str) -> str:
    """
    Function that works similar to the built-in string method :func:`str.capitalize`,
    except that it only makes the first character uppercase, and leaves the other characters unchanged.

    :param text:    The string to capitalize.
    """
    _vld.pass_if(_vld.is_text(text), TypeError, "'text' attribute must be a string (got {!r})".format(text))
    if len(text) < 2:
        return text.upper()
    return f'{text[0].upper()}{text[1:]}'


def unquote(text: str) -> str:
    """
    Strips trailing quotes from a text string and returns it.

    :param text:    The string to strip.
    """
    _vld.pass_if(_vld.is_text(text), TypeError, "'text' attribute must be a string (got {!r})".format(text))
    return text.strip('\'"`')


def format_plural(word: str, number: _Number, plural_suffix: str = 's') -> str:
    """
    Function that prefixes `word` with `number` and appends `plural_suffix` to it if `number` <> 1.
    Note that this only works for words with simple conjugation (where the base word and suffix do not change).
    E.g. words like 'sheep' or 'life' will be falsely pluralized ('sheeps' and 'lifes' respectively).

    Examples:

        >>> format_plural('{} error', 42)
        '42 errors'

        >>> format_plural('{} bus', 99, 'es')
        '99 buses'

        >>> format_plural('{} goal', 1)
        '1 goal'

        >>> format_plural('{} regret', 0)
        '0 regrets'

    :param word:            The word that should be pluralized if `number` <> 1.
    :param number:          The numeric value for which `word` will be prefixed and pluralized.
    :param plural_suffix:   If `word` is a constant and the `plural_suffix` for it cannot be 's', set your own.
    """
    # Argument validation
    _vld.pass_if(_vld.is_number(number), TypeError, "'number' attribute must be numeric")
    _vld.pass_if(_vld.is_text(word, False), TypeError, "'word' attribute must be a non-empty string")
    _vld.pass_if(word[-1].isalpha(), ValueError, "'word' must end with an alphabetic character")

    if number == 1:
        plural_suffix = _const.CHAR_EMPTY
    return _const.CHAR_EMPTY.join((str(number), _const.CHAR_SPACE, word, plural_suffix))


def format_iterable(iterable: _tp.Union[list, tuple], conjunction: str = _const.TEXT_AND) -> str:
    """
    Function that pretty-prints an iterable, separated by commas and adding a conjunction before the last item.

    Example:

        >>> iterable = [1, 2, 3, 4]
        >>> format_iterable(iterable)
        '1, 2, 3 and 4'

    :param iterable:    The iterable (e.g. list or tuple) to format.
    :param conjunction: The conjunction to use before the last item. Defaults to "and".
    """
    _vld.pass_if(_vld.is_iterable(iterable), TypeError, "'iterable' attribute must be an iterable (e.g. list)")

    num_items = len(iterable)
    if num_items == 0:
        return ''
    if num_items == 1:
        return to_str(iterable[-1])
    return '{} {} {}'.format(', '.join(to_str(v) for v in iterable[:-1]), conjunction, iterable[-1])


def format_timedelta(start: _dt, stop: _dt = None) -> str:
    """
    Calculates the time difference between `start` and `stop` datetime objects and returns a pretty-printed time delta.
    If `stop` is omitted, the current time (:func:`now`) will be used.
    The smallest time unit that can be expressed is in (floating point) seconds. The largest time unit is in days.

    Example:

        >>> t0 = _dt(2019, 1, 1, 1, 1, 1)  # where _dt = datetime
        >>> format_timedelta(t0)
        '1 day, 3 hours, 4 minutes and 5.2342 seconds'

    :param start:   The start time (t0) for the time delta calculation.
    :param stop:    The end time (t1) for the time delta calculation or :func:`now` when omitted.
    """
    # Attribute validation
    _vld.pass_if(isinstance(start, _dt), TypeError, "'start' attribute must be a datetime instance")
    _vld.pass_if(not stop or isinstance(stop, _dt), TypeError, "'stop' attribute must be a datetime instance (or None)")

    td = abs((stop or _dt.now()) - start)
    total_h, rem = divmod(td.total_seconds(), 3600)
    d, h = divmod(total_h, 24)
    m, s = divmod(rem, 60)
    t_comp = (format_plural(f, t)
              for f, t in
              (('day', int(d)), ('hour', int(h)), ('minute', int(m)), ('second', s))
              if t > 0)
    return format_iterable([t for t in t_comp] or ['0 seconds'])
