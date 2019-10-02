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

from decimal import Decimal

import pytest

from gpf.common import validate


def test_hasvalue():
    assert validate.has_value('') is False
    assert validate.has_value(None) is False
    assert validate.has_value([]) is False
    assert validate.has_value({}) is False
    assert validate.has_value('a') is True
    assert validate.has_value(0) is True
    assert validate.has_value(1) is True
    assert validate.has_value(3.14) is True
    assert validate.has_value(u'Test') is True
    assert validate.has_value('  ', True) is False
    assert validate.has_value(0, True) is True
    assert validate.has_value(None, True) is False
    assert validate.has_value(u'Panaché') is True


def test_isnumber():
    assert validate.is_number(3.14) is True
    assert validate.is_number(0) is True
    assert validate.is_number(False) is False
    assert validate.is_number(True) is False
    assert validate.is_number(False, True) is True
    assert validate.is_number(True, True) is True
    assert validate.is_number('test') is False
    assert validate.is_number(None) is False
    assert validate.is_number(Decimal('0.123456789')) is True


def test_istext():
    assert validate.is_text('test') is True
    assert validate.is_text('123') is True
    assert validate.is_text('') is True
    assert validate.is_text('', False) is False
    assert validate.is_text(None) is False
    assert validate.is_text(True) is False
    assert validate.is_text(' ') is True
    assert validate.is_text(' ', False) is True
    assert validate.is_text(1) is False


def test_isiterable():
    assert validate.is_iterable([1, 2, 3]) is True
    assert validate.is_iterable((1, 2, 3)) is True
    assert validate.is_iterable({1, 2, 3}) is False
    assert validate.is_iterable({'a': 1, 'b': 2}) is True
    assert validate.is_iterable(v for v in (1, 2, 3)) is False
    assert validate.is_iterable('test') is False
    assert validate.is_iterable(0) is False
    assert validate.is_iterable(None) is False


def test_raiseif():
    with pytest.raises(TypeError):
        validate.raise_if(True is True, 'bad', 'test')
    with pytest.raises(TypeError):
        validate.raise_if(True is True, TypeError, 'type fail')
    validate.raise_if(True is False, Exception, 'pass if False')


def test_passif():
    with pytest.raises(TypeError):
        validate.pass_if(True is False, 'bad', 'test')
    with pytest.raises(ValueError):
        validate.pass_if(True is False, ValueError, 'value fail')
    validate.pass_if(True is True, Exception, 'pass if True')
