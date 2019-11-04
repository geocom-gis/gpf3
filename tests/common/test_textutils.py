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

from datetime import datetime as dt

import pytest

from gpf.common import const
from gpf.common import textutils


# noinspection PyTypeChecker
def test_getalphachars():
    assert textutils.get_alphachars('--test--') == 'test'
    assert textutils.get_alphachars('test123') == 'test'
    assert textutils.get_alphachars('123') == const.CHAR_EMPTY
    with pytest.raises(TypeError):
        textutils.get_alphachars(None)
        textutils.get_alphachars(123)


# noinspection PyTypeChecker
def test_getdigits():
    assert textutils.get_digits('--test--') == const.CHAR_EMPTY
    assert textutils.get_digits('test123') == '123'
    assert textutils.get_digits('123') == '123'
    with pytest.raises(TypeError):
        textutils.get_digits(None)
        textutils.get_digits(123)


def test_tostr():
    assert textutils.to_str(5) == '5'
    assert textutils.to_str('täst') == 'täst'
    assert textutils.to_str('test') == 'test'
    assert textutils.to_str(b'test') == 'test'


def test_tobytes():
    assert textutils.to_bytes(7) == b'\x00\x00\x00\x00\x00\x00\x00'
    assert textutils.to_bytes('test') == b'test'
    assert textutils.to_bytes('täst'.encode('utf8')) == bytes('täst'.encode())
    assert textutils.to_bytes('täst') == 'täst'.encode('utf8')
    assert textutils.to_bytes('täst'.encode('cp1252')) == 'täst'.encode('cp1252')
    assert textutils.to_bytes('täst', 'utf16') == b'\xff\xfet\x00\xe4\x00s\x00t\x00'


def test_torepr():
    assert textutils.to_repr(3.14) == '3.14'
    assert textutils.to_repr('täst') == repr('täst')
    assert textutils.to_repr('test') == repr('test')
    assert textutils.to_repr(object()).startswith('<object object at 0x')


def test_capitalize():
    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        textutils.capitalize(666)
    assert textutils.capitalize('') == ''
    assert textutils.capitalize('a') == 'A'
    assert textutils.capitalize(u'hello world') == u'Hello world'
    assert textutils.capitalize('this IS A TeST') == 'This IS A TeST'


def test_unquote():
    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        textutils.unquote(666)
    assert textutils.unquote("'hello'") == 'hello'
    assert textutils.unquote("""hello""") == 'hello'
    assert textutils.unquote('"hello"') == 'hello'
    assert textutils.unquote('\'He said "Hello"!`') == 'He said "Hello"!'
    assert textutils.unquote(repr('Hello World')) == 'Hello World'


# noinspection PyTypeChecker
def test_formatplural():
    assert textutils.format_plural('test', 0) == '0 tests'
    assert textutils.format_plural('test', 1) == '1 test'
    assert textutils.format_plural('test', 2) == '2 tests'
    assert textutils.format_plural('test', 3.14) == '3.14 tests'
    assert textutils.format_plural('bus', 2, 'es') == '2 buses'
    with pytest.raises(TypeError):
        textutils.format_plural(1, 'test')
        textutils.format_plural(None, 1)
        textutils.format_plural('test', None)
    with pytest.raises(ValueError):
        textutils.format_plural('123', 0)
        textutils.format_plural('--test--', 1)


# noinspection PyTypeChecker
def test_formatiterable():
    assert textutils.format_iterable([1, 2, 3]) == '1, 2 and 3'
    assert textutils.format_iterable([1, 2]) == '1 and 2'
    assert textutils.format_iterable(('trick', 'treat'), const.TEXT_OR) == 'trick or treat'
    assert textutils.format_iterable([1]) == '1'
    assert textutils.format_iterable([]) == ''
    with pytest.raises(TypeError):
        textutils.format_iterable(v for v in [1, 2, 3])
        textutils.format_iterable('test')


# noinspection PyTypeChecker
def test_formattimedelta():
    assert textutils.format_timedelta(dt.now()) in ('0 seconds', '0.001 seconds')
    assert textutils.format_timedelta(dt(2019, 1, 1), dt(2019, 1, 1)) in ('0 seconds', '0.001 seconds')
    assert textutils.format_timedelta(dt(2019, 1, 1), dt(2019, 2, 1)) == '31 days'
    assert textutils.format_timedelta(dt(2019, 1, 1), dt(2019, 2, 1, 1)) == '31 days and 1 hour'
    assert textutils.format_timedelta(dt(2019, 1, 1),
                                      dt(2019, 1, 2, 2, 3, 4)) == '1 day, 2 hours, 3 minutes and 4.0 seconds'
    with pytest.raises(TypeError):
        textutils.format_timedelta('test')
        textutils.format_timedelta(dt(2019, 1, 1), 'test')
