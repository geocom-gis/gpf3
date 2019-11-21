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

import pytest

from gpf.tools.queries import *


# noinspection PyTypeChecker
def test_where_bad_init():
    with pytest.raises(ValueError):
        Where('')
        Where(None)


def test_where_in():
    assert str(Where('A').In([1, 2, 3])) == 'A IN (1, 2, 3)'
    assert str(Where('B').In((1, 2, 3))) == 'B IN (1, 2, 3)'
    assert str(Where('C').In(2, 3, 2, 1, 3)) == 'C IN (1, 2, 3)'
    assert str(Where('D').In('a', 'c', 'd', 'a')) == 'D IN (\'a\', \'c\', \'d\')'
    assert str(Where('E').In(4, 3.456)) == 'E IN (3.456, 4)'
    with pytest.raises(ValueError):
        Where('F').In(object(), 'a', 2)
        Where('G').In((1, 'a', 5.6))
    assert str(Where('H').NotIn('Test1', 'Test2')) == 'H NOT IN (\'Test1\', \'Test2\')'
    assert str(Where('I').NotIn('a')) == 'I NOT IN (\'a\')'


def test_where_between():
    assert str(Where('A').Between((5, 10))) == 'A BETWEEN 5 AND 10'
    assert str(Where('B').Between('a', 'z')) == 'B BETWEEN \'a\' AND \'z\''
    assert str(Where('C').NotBetween(10, 1)) == 'C NOT BETWEEN 1 AND 10'
    assert str(Where('D').Between(1, 2, 3, 4)) == 'D BETWEEN 1 AND 4'
    assert str(Where('E').NotBetween([5, 8, 1, 0])) == 'E NOT BETWEEN 0 AND 8'
    with pytest.raises(ValueError):
        Where('F').Between(2)


def test_where_like():
    assert str(Where('A').Like('Test%')) == 'A LIKE \'Test%\''
    assert str(Where('B').NotLike('Test_')) == 'B NOT LIKE \'Test_\''
    # The following line produces bad SQL, but this is the users responsibility:
    assert str(Where('C').Like('%10$%%')) == 'C LIKE \'%10$%%\''
    assert str(Where('D').Like('%10$%%', escape_char='$')) == 'D LIKE \'%10$%%\' ESCAPE \'$\''


def test_where_null():
    assert str(Where('A').IsNull()) == 'A IS NULL'
    assert str(Where('B').IsNotNull()) == 'B IS NOT NULL'


def test_where_compare():
    assert str(Where('A').Equals(1)) == 'A = 1'
    assert str(Where('B').NotEquals(2)) == 'B <> 2'
    assert str(Where('C').LessThan(1)) == 'C < 1'
    assert str(Where('D').GreaterThan(True)) == 'D > 1'
    assert str(Where('E').LessThanOrEquals(4.2)) == 'E <= 4.2'
    assert str(Where('F').GreaterThanOrEquals('test')) == 'F >= \'test\''
    assert str(Where('G').Equals("Monty Python's Flying Circus")) == 'G = "Monty Python\'s Flying Circus"'
    assert str(Where('H').NotEquals(
            "We're the knights who say \"Ni\"!")) == 'H <> \'We\\\'re the knights who say "Ni"!\''


def test_where_chains():
    assert str(Where('A').Between(5, 10).And('B').Like('%test')) == 'A BETWEEN 5 AND 10 AND B LIKE \'%test\''
    assert str(combine(
            Where('A').Equals(True).And('B').Equals(False)).Or('C').IsNull()) == '( A = 1 AND B = 0 ) OR C IS NULL'
    assert str(Where('A').Equals(1).And('B').Equals(0).Or('C').IsNull()) == 'A = 1 AND B = 0 OR C IS NULL'


def test_where_fields():
    assert Where('A').Equals(1).And('B').Equals(0).Or('C').IsNull().fields == ('A', 'B', 'C')


def test_where_kwargs():
    assert Where('Täst').IsNull().get_kwargs() == {'where_clause': 'Täst IS NULL'}


def test_add_kwargs():
    keywords = {'test': 0}
    assert add_where(keywords, Where('A').LessThan(4)) is None
    assert keywords == {'test': 0, 'where_clause': 'A < 4'}
