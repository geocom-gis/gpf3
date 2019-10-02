# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

import pytest

from geocom.tools.queries import InitError
from geocom.tools.queries import OperatorError
from geocom.tools.queries import Where


# noinspection PyTypeChecker
def test_where_bad_init():
    with pytest.raises(InitError):
        Where('', None)
        Where(None, 'in')
        Where('FieldName')
    with pytest.raises(OperatorError):
        Where('A', 'unlike', 1)
    with pytest.raises(OverflowError):
        w = Where('B', 'like', 'you')
        # test that the private _add_expression() can't be called explicitly
        w._add_expression('and not like', 'me')


def test_where_in():
    assert str(Where('A', 'in', [1, 2, 3])) == 'A IN (1, 2, 3)'
    assert str(Where('B', 'in', (1, 2, 3))) == 'B IN (1, 2, 3)'
    assert str(Where('C', 'in', 2, 3, 2, 1, 3)) == 'C IN (1, 2, 3)'
    assert str(Where('D', 'in', ('a', 'c', 'd', 'a'))) == 'D IN (\'a\', \'c\', \'d\')'
    assert str(Where('E', 'in', (4, 3.456))) == 'E IN (3.456, 4)'
    with pytest.raises(TypeError):
        Where('F', 'in', (object(), 'a', 2))
        Where('G', 'in', (1, 'a', 5.6))
    # assert str(Where('H', 'not in', (u'Test1', 'Test2'))) == 'H NOT IN (\'Test1\', \'Test2\')'  FIXME
    assert str(Where('I', 'not in', 'a')) == 'I NOT IN (\'a\')'


def test_where_between():
    assert str(Where('A', 'between', (5, 10))) == 'A BETWEEN 5 AND 10'
    assert str(Where('B', 'between', ('a', 'z'))) == 'B BETWEEN \'a\' AND \'z\''
    assert str(Where('C', '  Not Between  ', (10, 1))) == 'C NOT BETWEEN 1 AND 10'
    assert str(Where('D', 'between', 1, 2, 3, 4)) == 'D BETWEEN 1 AND 4'
    assert str(Where('D', 'not between', [5, 8, 1, 0])) == 'D NOT BETWEEN 0 AND 8'
    with pytest.raises(OperatorError):
        Where('E', 'between', 2)
        Where('F', '=')


def test_where_like():
    assert str(Where('A', 'like', 'Test%')) == 'A LIKE \'Test%\''
    assert str(Where('B', 'not like', 'Test_')) == 'B NOT LIKE \'Test_\''
    # The following line produces bad SQL, but this is the users responsibility:
    assert str(Where('C', 'like', '%10$%%')) == 'C LIKE \'%10$%%\''


def test_where_null():
    assert str(Where('A', 'IS NULL')) == 'A IS NULL'
    assert str(Where('B', 'is not null')) == 'B IS NOT NULL'


def test_where_compare():
    assert str(Where('A', '=', 1)) == 'A = 1'
    assert str(Where('B', '!=', 2)) == 'B != 2'
    assert str(Where('B', '<>', 2)) == 'B <> 2'
    assert str(Where('C', '<', 1)) == 'C < 1'
    assert str(Where('D', '>', True)) == 'D > 1'
    assert str(Where('E', '<=', 4.2)) == 'E <= 4.2'
    assert str(Where('F', '>=', 'test')) == 'F >= \'test\''
    assert str(Where('G', '=', "Monty Python's Flying Circus")) == 'G = "Monty Python\'s Flying Circus"'
    assert str(Where('H', '!=', "We're the knights who say \"Ni\"!")) == 'H != \'We\\\'re the knights who say "Ni"!\''


def test_where_chain():
    assert str(Where('A', 'between', 5, 10) &
               Where('B', 'like', '%1$%%')) == 'A BETWEEN 5 AND 10 AND B LIKE \'%1$%%\''
    assert str(Where(Where('A', '=', True) & Where('B', '=', False)) |
               Where('C', 'is null')) == '( A = 1 AND B = 0 ) OR C IS NULL'
    assert str(Where('A', '=', 1) & Where('B', '=', 0) |
               Where('C', 'is null')) == 'A = 1 AND B = 0 OR C IS NULL'
