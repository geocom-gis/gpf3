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
Module that facilitates working with basic SQL expressions and where clauses in ArcGIS.
"""

import typing as _tp
from functools import wraps as _wraps

import more_itertools as _iter

import gpf.common.const as _const
import gpf.common.guids as _guids
import gpf.common.textutils as _tu
import gpf.common.validate as _vld
from gpf import arcpy as _arcpy
from gpf.paths import Workspace as _Ws

WHERE_KWARG = 'where_clause'


def _return_new(func):
    """ Decorator function to execute instance method *func* on a new copy of the original instance. """
    @_wraps(func)
    def wrapped(instance, *args, **kwargs):
        cls = instance.__class__
        new_instance = cls(instance)
        func(new_instance, *args, **kwargs)
        return new_instance
    return wrapped


# noinspection PyPep8Naming
class Where(object):
    """
    Where(field_or_clause)

    Basic query helper class to build basic SQL expressions for ArcPy tools where clauses.
    Because all methods return a new instance, the user can "daisy chain" multiple statements.

    When used in combination with the :py:mod:`gpf.cursors` module, the Where clause can be passed-in directly.
    In other cases (e.g. *arcpy* tools), the resulting SQL expression is obtained using :func:`str`, :func:`unicode`
    or :func:`repr`. Note that the first 2 functions check if the resulting expression is a complete SQL query.
    Since Esri's *arcpy* prefers ``unicode`` text, the :func:`unicode` function is recommended over the :func:`str`.

    Example of a simple query:

        >>> Where('A').GreaterThanOrEquals(3.14)
        A >= 3.14

    The :func:`In` and :func:`NotIn` functions accept multiple arguments or an iterable as input.
    The following example shows how boolean values are interpreted as integers and that duplicates are removed:

        >>> Where('A').NotIn(1, 2, True, False, 3)
        A NOT IN (0, 1, 2, 3)

    The :func:`Between` and :func:`NotBetween` functions also accept multiple arguments or an iterable as input.
    The resulting SQL expression will only use the lower and upper values of the input list,
    as shown in the following composite query example:

        >>> Where('A').Like('Test%').Or('B').Between([8, 5, 3, 4])
        A LIKE 'Test%' OR B BETWEEN 3 AND 8

    The following example demonstrates how you can make a grouped composite query using the :func:`combine` function:

        >>> combine(Where('A').Equals(1).And('B').Equals(0)).Or('C').IsNull()
        (A = 1 AND B = 0) OR C IS NULL

    **Params:**

    -   **where_field** (str, unicode, gpf.tools.queries.Where):

        The initial field to start the where clause, or another `Where` instance.
    """

    # Private class constants
    __SQL_OR = _const.TEXT_OR.upper()
    __SQL_AND = _const.TEXT_AND.upper()
    __SQL_NOT = 'NOT'
    __SQL_IS = 'IS'
    __SQL_IN = 'IN'
    __SQL_NULL = 'NULL'
    __SQL_LIKE = 'LIKE'
    __SQL_BETWEEN = 'BETWEEN'
    __SQL_ESCAPE = 'ESCAPE'
    __SQL_EQ = '='
    __SQL_LE = '<='
    __SQL_GE = '>='
    __SQL_LT = '<'
    __SQL_GT = '>'
    __SQL_NE = '<>'

    def __init__(self, field_or_clause: _tp.Union[str, 'Where']):
        self._parts = []
        self._isdirty = False
        self._add_new(field_or_clause)

    def __repr__(self):
        """
        Returns the where clause SQL string representation of this Where instance.
        Note that str() and repr() will both return the same string when called on the instance.
        However, repr() does not check if the constructed query is valid.

        :return:    A where clause SQL expression string.
        """
        return self._output()

    def __str__(self):
        """
        Returns the where clause SQL encoded string representation of this Where instance.

        :return:            A where clause SQL expression string.
        :rtype:             str
        :raises ValueError: If the query has not been finished properly.
        """
        return self._output(True)

    def __eq__(self, other) -> bool:
        """ Returns ``True`` when the other object is of the same type and/or represents the same SQL expression. """
        if isinstance(other, str):
            return repr(self) == other
        elif isinstance(other, Where):
            return repr(self) == repr(other)
        return False

    def _add_any(self, value: _tp.Any, is_field: bool = False, is_conjunction: bool = False):
        """ Generic method to add a new part (field name, operator, or value) to the current query. """
        if (is_field or is_conjunction) == self._isdirty:
            raise SyntaxError(f'Adding {value!r} would create an invalid query')
        self._parts.append((value, is_field))

    def _add_expression(self, *values):
        """ Adds an expression (consisting of multiple parts) to the current query. """
        for v in values:
            self._add_any(v)
        self._isdirty = False

    def _add_field(self, field: str):
        """  Adds a field to the query (combine or init). """
        self._add_any(field, True)
        self._isdirty = True

    def _add_clause(self, clause: 'Where'):
        """
        Adds another clause to the query (combine or init).

        :type clause:   Where
        """
        # Copy all parts
        self._parts.extend(clause._parts)

        # Copy the _isdirty state of the input query
        self._isdirty = clause._isdirty

    def _add_new(self, field_or_clause: _tp.Union[str, 'Where']):
        """ Adds a new field or a complete clause to the current query. """
        if isinstance(field_or_clause, Where):
            # Add a whole Where clause
            return self._add_clause(field_or_clause)

        if isinstance(field_or_clause, str):
            # Add a new field and set state to dirty
            return self._add_field(field_or_clause)

        # At this point, the passed-in argument is invalid
        raise ValueError(f"'field_or_clause' must be a field name or {self.__class__.__name__} instance")

    def _combine(self, operator: str, field_or_clause: _tp.Union[str, 'Where']):
        """ Instructs Where instance to append a new query using the AND or OR conjunction. """
        self._add_any(operator, is_conjunction=True)
        self._add_new(field_or_clause)

    def _output(self, check: bool = False):
        """ Concatenates all query parts to form an actual SQL expression. Can check if the query is dirty. """
        _vld.raise_if(check and self._isdirty, ValueError, 'Cannot output invalid query')
        return f"""{_const.CHAR_SPACE.join(part for part, _ in self._parts)}"""

    @staticmethod
    def _check_types(*args) -> bool:
        """ Checks that all query values have compatible data types. Applies to IN and BETWEEN operators. """

        # Check that none of the arguments are of type 'object' (this breaks the type check)
        _vld.raise_if(any(v.__class__ is object for v in args),
                      ValueError, f'Values of type object are not allowed in IN and BETWEEN queries')

        # Get the first value and get its type
        sample_val = args[0]
        sample_type = type(sample_val)

        # Allow for some flexibility concerning numbers
        if _vld.is_number(sample_val, True):
            # For now, we will allow a mixture of floats and integers (and bools) in the list of values
            sample_type = (int, float, bool)

        return all(isinstance(v, sample_type) for v in args)

    @staticmethod
    def _format_value(value: _tp.Any) -> str:
        """
        Private method to format *value* for use in an SQL expression based on its type.
        This basically means that all non-numeric values (strings) will be quoted.
        If value is a :class:`gpf.common.guids.Guid` instance, the result will be wrapped in curly braces and quoted.

        :param value:   Any value. Single quotes in strings will be escaped automatically.
        :return:        A formatted string.
        :rtype:         unicode
        """
        if _vld.is_number(value, True):
            # Note: a `bool` is of instance `int` but calling format() on it will return a string (True or False).
            # To prevent this from happening, we'll use the `real` numeric part instead (on int, float and bool).
            return str(value.real)

        if isinstance(value, _guids.Guid):
            # Parse Guid instances as strings
            value = str(value)
        if _vld.is_text(value):
            return _tu.to_repr(value)

        raise ValueError('All values in an SQL expression must be text strings or numeric values')

    def _check_values(self, values: _tp.Sequence, min_required: int, operator: str) -> list:
        """ Flattens the IN/BETWEEN query values, performs several checks, and returns the list if ok. """
        output = [v for v in _iter.collapse(values, levels=1)]
        _vld.pass_if(len(output) >= min_required,
                     ValueError, f'{operator} query requires at least {min_required} value')
        _vld.pass_if(self._check_types(*output),
                     ValueError, f'{operator} query values must have similar data types')
        return output

    def _in(self, operator: str, *values):
        """ Adds an (NOT) IN expression to the SQL query. """
        flat_values = self._check_values(values, 1, operator)
        expression = f'({_const.TEXT_COMMASPACE.join((self._format_value(v) for v in sorted(frozenset(flat_values))))})'
        self._add_expression(operator, expression)

    def _between(self, operator: str, *values):
        """ Adds a (NOT) BETWEEN .. AND .. expression to the SQL query. """
        flat_values = self._check_values(values, 2, operator)
        lower, upper = (self._format_value(v) for v in (min(flat_values), max(flat_values)))
        self._add_expression(operator, lower, self.__SQL_AND, upper)

    def _like(self, operator: str, value: _tp.Any, escape_char: _tp.Union[str, None]):
        """ Adds a (NOT) LIKE expression to the SQL query. """
        expression = [self._format_value(value)]
        if escape_char:
            expression += [self.__SQL_ESCAPE, self._format_value(escape_char)]
        self._add_expression(operator, _const.CHAR_SPACE.join(expression))

    # The following method names do NOT conform to PEP8 conventions.
    # However, this is done for the sake of consistency and readability,
    # since some lowercase method names like "and" or "or" would otherwise
    # conflict with Python's built-in operators.
    # Furthermore, since all these methods return a new Where instance,
    # using Pascal case makes it clear that these methods are "special".

    @_return_new
    def And(self, field_or_clause: _tp.Union[str, 'Where']):
        """
        Adds a new field or another SQL query to a new instance of the current SQL query,
        separated by an "AND" statement and returns it.

        :param field_or_clause:     A field name or another ``Where`` instance.
        :type field_or_clause:      str, unicode, Where
        :rtype:                     Where
        """
        self._combine(self.__SQL_AND, field_or_clause)

    @_return_new
    def Or(self, field_or_clause: _tp.Union[str, 'Where']):
        """
        Adds a new field or another SQL query to a new instance of the current SQL query,
        separated by an "OR" statement and returns it.

        :param field_or_clause:     A field name or another ``Where`` instance.
        :type field_or_clause:      str, unicode, Where
        :rtype:                     Where
        """
        self._combine(self.__SQL_OR, field_or_clause)

    @_return_new
    def In(self, *values):
        """
        Adds an IN expression to a copy of the current instance to complete the SQL query and returns it.
        The given input values must have similar data types. The values will be ordered and duplicates are removed.

        :rtype: Where
        """
        self._in(self.__SQL_IN, *values)

    @_return_new
    def NotIn(self, *values):
        """
        Adds a NOT IN expression to a copy of the current instance to complete the SQL query and returns it.
        The given input values must have similar data types. The values will be ordered and duplicates are removed.

        :rtype: Where
        """
        self._in(self.__SQL_NOT + _const.CHAR_SPACE + self.__SQL_IN, *values)

    @_return_new
    def Between(self, *values):
        """
        Adds a BETWEEN expression to a copy of the current instance to complete the SQL query and returns it.
        The given input values must have similar data types. Only the lower and upper values are used.

        :rtype: Where
        """
        self._between(self.__SQL_BETWEEN, *values)

    @_return_new
    def NotBetween(self, *values):
        """
        Adds a NOT BETWEEN expression to a copy of the current instance to complete the SQL query and returns it.
        The given input values must have similar data types. Only the lower and upper values are used.

        :rtype: Where
        """
        self._between(self.__SQL_NOT + _const.CHAR_SPACE + self.__SQL_BETWEEN, *values)

    @_return_new
    def Like(self, value: _tp.Any, escape_char: _tp.Union[None, str] = None):
        """
        Adds a LIKE expression to a copy of the current instance to complete the SQL query and returns it.
        Optionally, an escape character can be specified e.g. when a % symbol must be taken literally.

        :rtype: Where
        """
        self._like(self.__SQL_LIKE, value, escape_char)

    @_return_new
    def NotLike(self, value: _tp.Any, escape_char: _tp.Union[None, str] = None):
        """
        Adds a NOT LIKE expression to a copy of the current instance to complete the SQL query and returns it.
        Optionally, an escape character can be specified e.g. when a % symbol must be taken literally.

        :rtype: Where
        """
        self._like(self.__SQL_NOT + _const.CHAR_SPACE + self.__SQL_LIKE, value, escape_char)

    @_return_new
    def Equals(self, value: _tp.Any):
        """
        Adds a "=" expression to a copy of the current instance to complete the SQL query and returns it.

        :rtype: Where
        """
        self._add_expression(self.__SQL_EQ, self._format_value(value))

    @_return_new
    def NotEquals(self, value: _tp.Any):
        """
        Adds a "<>" expression to a copy of the current instance to complete the SQL query and returns it.

        :rtype: Where
        """
        self._add_expression(self.__SQL_NE, self._format_value(value))

    @_return_new
    def GreaterThan(self, value: _tp.Any):
        """
        Adds a ">" expression to a copy of the current instance to complete the SQL query and returns it.

        :rtype: Where
        """
        self._add_expression(self.__SQL_GT, self._format_value(value))

    @_return_new
    def LessThan(self, value: _tp.Any):
        """
        Adds a "<" expression to a copy of the current instance to complete the SQL query and returns it.

        :rtype: Where
        """
        self._add_expression(self.__SQL_LT, self._format_value(value))

    @_return_new
    def GreaterThanOrEquals(self, value: _tp.Any):
        """
        Adds a ">=" expression to a copy of the current instance to complete the SQL query and returns it.

        :rtype: Where
        """
        self._add_expression(self.__SQL_GE, self._format_value(value))

    @_return_new
    def LessThanOrEquals(self, value: _tp.Any):
        """
        Adds a "<=" expression to a copy of the current instance to complete the SQL query and returns it.

        :rtype: Where
        """
        self._add_expression(self.__SQL_LE, self._format_value(value))

    @_return_new
    def IsNull(self):
        """
        Adds a IS NULL expression to a copy of the current instance to complete the SQL query and returns it.

        :rtype: Where
        """
        self._add_any(self.__SQL_IS + _const.CHAR_SPACE + self.__SQL_NULL)
        self._isdirty = False

    @_return_new
    def IsNotNull(self):
        """
        Adds a IS NOT NULL expression to a copy of the current instance to complete the SQL query and returns it.

        :rtype: Where
        """
        self._add_any(_const.CHAR_SPACE.join((self.__SQL_IS, self.__SQL_NOT, self.__SQL_NULL)))
        self._isdirty = False

    def get_kwargs(self, keyword=WHERE_KWARG, **kwargs) -> dict:
        """
        Returns the where clause SQL string representation as a *keyword=value* ``dict``.

        This can be used in combination with the double-asterisk syntax (``**``) in an *arcpy* tool call, for example.
        If this function is called with existing keyword arguments, the SQL where clause will be appended/updated.

        :param keyword:     The name of the SQL keyword argument. By default, this is ``where_clause``.
        :param kwargs:      An optional existing keyword dictionary to which the where clause should be added.
        :return:            A keyword dictionary containing the ``where_clause`` key-value pair.
        """
        kwargs[keyword] = self._output()
        return kwargs

    def delimit_fields(self, datasource: _tp.Union[str, _Ws]):
        """
        Updates the fields in the query by wrapping them in the appropriate delimiters for the current data source.

        :param datasource:  The path to the data source (e.g. SDE connection, feature class, etc.)
                            or a :class:`gpf.paths.Workspace` instance.

        .. seealso::        https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-functions/addfielddelimiters.htm
        """
        for i, (part, is_field) in enumerate(self._parts):
            if not is_field:
                continue
            # Call arcpy function on "clean" version of the field name (to prevent adding duplicate delimiters)
            part = _arcpy.AddFieldDelimiters(
                    _tu.to_str(datasource) if isinstance(datasource, _Ws) else datasource, part.strip('[]"'))
            self._parts[i] = (part, is_field)

    @property
    def fields(self) -> tuple:
        """
        Returns a tuple of all fields (in order of occurrence) that currently participate in the ``Where`` clause.
        """
        return tuple(part for part, is_field in self._parts if is_field)

    @property
    def is_ready(self) -> bool:
        """ Returns ``True`` when the query appears to be ready for execution (i.e. has no syntax errors). """
        return not self._isdirty


# noinspection PyProtectedMember
def combine(where_clause: Where) -> Where:
    """
    The `combine` function wraps a :class:`Where` instance in parenthesis "()".
    This is typically used to combine 2 or more SQL clauses (delimited by AND or OR) into one.

    Example:

        >>> combine(Where('A').Equals(1).And('B').Equals(0)).Or('C').IsNull()
        (A = 1 AND B = 0) OR C IS NULL

    **Params:**

    -   **where_clause** (:class:`Where`):

        Another `Where` instance that should be wrapped in parenthesis.
    """

    # Check if clause is another Where instance
    _vld.pass_if(isinstance(where_clause, Where),
                 ValueError, f'Input clause must be of type {Where.__name__!r}')

    # Since we will wrap the query in parenthesis, it must be a complete query (not dirty)
    _vld.pass_if(where_clause.is_ready, ValueError, 'Cannot wrap incomplete query in parenthesis')

    wrapper = Where(where_clause)
    wrapper._parts.insert(0, ('(', False))
    wrapper._parts.append((')', False))
    return wrapper


def add_where(keyword_args: dict, where_clause: _tp.Union[str, Where],
              datasource: _tp.Union[None, str, _Ws] = None) -> None:
    """
    Updates the keyword arguments dictionary with a where clause (string or ``Where`` instance).

    :param keyword_args:    A keyword argument dictionary.
    :param where_clause:    A query string or a :class:`Where` instance.
    :param datasource:      If the data source path is specified, the field delimiters are updated accordingly.
                            This only has an effect if *where_clause* is a :class:`Where` instance.
    :raises ValueError:     If *where_clause* is not a string or :class:`Where` instance,
                            or if *keyword_args* is not a ``dict``.
    """
    if not where_clause:
        return

    _vld.pass_if(isinstance(keyword_args, dict), ValueError, 'keyword_args must be a dict')

    if isinstance(where_clause, Where):
        if datasource:
            where_clause.delimit_fields(datasource)
        keyword_args[WHERE_KWARG] = str(where_clause)
    elif isinstance(where_clause, str):
        keyword_args[WHERE_KWARG] = where_clause
    else:
        raise ValueError(f'{WHERE_KWARG!r} must be a string or {Where.__name__} instance')
