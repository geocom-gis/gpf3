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

import more_itertools as _iter

import gpf.common.guids as _guids
import gpf.common.textutils as _tu
import gpf.common.validate as _vld
from gpf.tools import arcpy as _arcpy

WHERE_KWARG = 'where_clause'
_CHECK_ARG = 'check_only'


# Wrappers for handled exceptions
class OperatorError(TypeError):
    """ Raised when an incorrect SQL operator is specified in a :class:`Where` instance. """
    pass


class InitError(TypeError):
    """ Raised when a :class:`Where` instance failed to initialize (i.e. because of bad arguments). """
    pass


class Where(object):
    """
    Where(where_field, {operator}, {values})

    Basic query helper class to build basic SQL expressions for ArcPy tools where clauses.
    Using the ``&`` and ``|`` bitwise operators, a user can "daisy chain" multiple statements.
    When used in combination with the :py:mod:`gpf.tools.cursors` module, the Where clause can be passed-in directly.
    In other cases (e.g. *arcpy* tools), the resulting SQL expression is obtained using ``str()`` or ``repr()``.

    Example of a simple query:

        >>> Where('A', '>=', 3.14)
        A >= 3.14

    The *(NOT) IN* operator accepts multiple arguments or an iterable as input.
    The following example shows how boolean values are interpreted as integers and that duplicates are removed:

        >>> Where('A', 'not in', [1, 2, True, False, 3])
        A NOT IN (0, 1, 2, 3)

    The *(NOT) BETWEEN* operator also accepts an iterable as input.
    The resulting SQL expression will only use the lower and upper bounds of the list,
    as shown in the following composite query example:

        >>> Where('A', 'like', 'Test%') | Where('B', 'between', [8, 5, 3, 4])
        A LIKE 'Test%' OR B BETWEEN 3 AND 8

    The following example demonstrates how you can make a grouped composite query using ``Where`` as a wrapper:

        >>> Where(Where('A', '=', 1) & Where('B', '=', 0)) | Where('C', 'is null')
        (A = 1 AND B = 0) OR C IS NULL

    :param where_field: The initial field to start the where clause, or another `Where` instance.
    :param operator:    Operator string (e.g. *between*, *in*, *<*, *=*, *is null*, etc.).
    :arg values:        The conditional values that must be met for the specified field and operator.
                        Multiple values and iterables will all be flattened (one level), sorted and de-duped.
                        For the *is null* and *is not null* operators, values will be ignored.
                        For all operators except *(not) between* and *(not) in*, only the first value will be used.
    :type where_field:  str, gpf.tools.queries.Where
    :type operator:     str
    """

    # Private class constants
    __SQL_OR = 'or'
    __SQL_AND = 'and'
    __SQL_IN = 'in'
    __SQL_NOT_IN = 'not in'
    __SQL_NULL = 'is null'
    __SQL_NOT_NULL = 'is not null'
    __SQL_LIKE = 'like'
    __SQL_NOT_LIKE = 'not like'
    __SQL_BETWEEN = 'between'
    __SQL_NOT_BETWEEN = 'not between'

    __SUPPORTED_OPERATORS = frozenset((
        '=', '<>', '!=', '<=', '>=', '<', '>',
        __SQL_NULL, __SQL_NOT_NULL, __SQL_IN, __SQL_NOT_IN,
        __SQL_LIKE, __SQL_NOT_LIKE, __SQL_BETWEEN, __SQL_NOT_BETWEEN
    ))

    def __init__(self, where_field: _tp.Union[str, None, 'Where'], operator: str = None, *values: _tp.Any):

        self._locked = False
        self._fields = {}
        self._parts = []
        if _vld.is_text(where_field, False) and operator:
            self._fields.setdefault(where_field.lower(), [0])
            self._parts.append(where_field)
            self._add_expression(operator, *values)
        elif isinstance(where_field, self.__class__):
            # When `where_field` is another Where instance, simply wrap its contents in parentheses
            self._update_fieldmap(where_field._fields, 1)
            self._parts = ['('] + where_field._parts + [')']
        elif where_field is not None:
            raise InitError('{0} expects a field name and an operator, or another {0} instance'.format(Where.__name__))

    def __or__(self, other) -> 'Where':
        """
        Override method of the bitwise OR operator `|` to combine the current SQL field expression with another one.

        Example:

            >>> Where('A', '>', 0) | Where('B', '=', 'example')
            A > 0 OR B = 'example'

        :param other:   Another ``Where`` instance.
        :return:        The combined new ``Where`` instance.
        """
        return self._combine(self.__SQL_OR, other)

    def __and__(self, other) -> 'Where':
        """
        Override method of the bitwise AND operator `&` to combine the current SQL field expression with another one.

        Example:

            >>> Where('A', '>', 0) & Where('B', '=', 'example')
            A > 0 AND B = 'example'

        :param other:   Another ``Where`` instance.
        :return:        The combined new ``Where`` instance.
        """
        return self._combine(self.__SQL_AND, other)

    def __repr__(self):
        """
        Returns the where clause SQL string representation of this Where instance.
        Note that str() and repr() will all return this string when called on the instance.

        :return:    A where clause SQL expression string.
        """
        return self._output()

    def __eq__(self, other):
        """ Returns ``True`` when the other object is of the same type and/or represents the same SQL expression. """
        if isinstance(other, str):
            return repr(self) == other
        elif isinstance(other, self.__class__):
            return repr(self) == repr(other)
        return False

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

    def fix_fields(self, datasource: str):
        """
        Updates the fields in the query by wrapping them in the appropriate delimiters for the current data source.

        :param datasource:  The path to the data source (e.g. SDE connection, feature class, etc.)

        .. seealso::        https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-functions/addfielddelimiters.htm
        """
        for field, indices in self._fields.items():
            for i in indices:
                self._parts[i] = _arcpy.AddFieldDelimiters(datasource, field)

    @property
    def fields(self) -> tuple:
        """
        Returns a sorted tuple of all fields that currently participate in the ``Where`` clause.
        """
        return tuple(sorted(self._fields))

    def _output(self) -> str:
        """
        Concatenates all query parts to form an actual SQL expression.

        :return:    An SQL expression string for ArcGIS tools.
        """
        return """{}""".format(_tu.SPACE.join(self._parts))

    def _add_expression(self, operator: str, *values: _tp.Any):
        """
        Private method to properly complete an SQL expression for the initial field.
        The current internal SQL expression will be permanently changed.
        Explicit consecutive calls to this function will raise an ``OverflowError``.

        :param operator:    The operator to use (=, <>, IN etc.).
        :param values:      The value(s) following the operator.
        """
        _vld.raise_if(self._locked, OverflowError, 'Cannot add more than one expression to a field')

        operator = self._fix_operator(operator)
        is_between = operator.endswith(self.__SQL_BETWEEN)
        self._parts.append(operator.upper())

        if operator not in (self.__SQL_NULL, self.__SQL_NOT_NULL):
            values = self._fix_values(*values, check_only=is_between)
            if operator.endswith(self.__SQL_IN):
                self._parts.append('({})'.format(', '.join(values)))
            elif is_between:
                self._between(operator, *values)
            else:
                self._parts.append(_iter.first(values))

        self._locked = True

    def _update_fieldmap(self, fieldmap: dict, offset: int):
        for k, values in fieldmap.items():
            fp_values = self._fields.setdefault(k, [])
            for v in values:
                fp_values.append(v + offset)

    # noinspection PyProtectedMember
    def _combine(self, operator: str, where: 'Where') -> 'Where':
        """
        Private method to append the SQL expression from another Where instance to the current one
        and return it as a new Where instance.

        :param operator:    The operator to use (AND/OR).
        :param where:       Another Where instance.
        :return:            The combined new Where instance.
        """
        _vld.pass_if(isinstance(where, self.__class__), TypeError, '{!r} is not a valid Where instance'.format(where))

        output = Where(None)
        output._fields = dict(self._fields)
        output._parts = list(self._parts)
        output._update_fieldmap(where._fields, len(where._parts) + 1)
        output._parts.append(operator.upper())
        output._parts.extend(where._parts)
        return output

    @staticmethod
    def _fix_operator(operator: str, allowed_operators: bool = __SUPPORTED_OPERATORS) -> str:
        """ Makes *operator* lowercase and checks if it's a valid operator. """
        operator = operator.strip().lower()
        _vld.pass_if(operator in allowed_operators, OperatorError,
                     'The {!r} operator is not allowed or supported'.format(operator))
        return operator

    def _fix_values(self, *values, **kwargs) -> _tp.Generator:
        """
        Private method to validate *values* for use in an SQL expression.
        All values, regardless if they are iterables themselves, will be flattened (up to 1 level).
        If the values do not have comparable types (i.e. all numeric, all strings), a ``TypeError`` will be raised.

        :param values:          An iterable (of iterables) with values to use for the SQL expression.
        :keyword check_only:    When False (default=True), values will be sorted and duplicates will be removed.
                                Furthermore, the returned values will be formatted for the SQL expression.
                                When True, the values will only be flattened and checked for comparable types.
        :return:                A generator of checked (and formatted) values.
        """
        _vld.pass_if(values, OperatorError, 'Specified {} operator requires at least one value'.format(Where.__name__))

        values = [v for v in _iter.collapse(values, levels=1)]
        unique_values = frozenset(values)
        first_val = _iter.first(unique_values)

        if _vld.is_number(first_val, True):
            # For now, allow a mixture of floats and integers (and bools) in the list of values
            # TODO: When input field is an arcpy.Field instance, filter by field.type
            first_type = (int, float, bool)
        elif _vld.is_text(first_val):
            first_type = str
        else:
            first_type = type(first_val)

        _vld.raise_if(any(not isinstance(v, first_type) for v in unique_values), TypeError,
                      'All {} values must have the same data type'.format(Where.__name__))

        check_only = kwargs.get(_CHECK_ARG, False)
        return (v if check_only else self._format_value(v) for v in (values if check_only else sorted(unique_values)))

    def _between(self, operator: str, *values):
        """ Adds a BETWEEN .. AND .. expression to the SQL query. """
        num_values = len(values)
        _vld.raise_if(num_values < 2, OperatorError,
                      '{} requires at least 2 values (got {})'.format(operator.upper(), num_values))
        lower, upper = (self._format_value(v) for v in (min(values), max(values)))
        self._parts.extend([lower, self.__SQL_AND.upper(), upper])

    @staticmethod
    def _format_value(value) -> str:
        """
        Private method to format *value* for use in an SQL expression based on its type.
        This basically means that all non-numeric values will be quoted.
        If value is a :class:`gpf.common.guids.Guid` string, the result will be wrapped in curly braces and quoted.

        :param value:   Any value. Single quotes in strings will be escaped automatically.
        :return:        A formatted string.
        """
        if _vld.is_number(value, True):
            # Note: a `bool` is of instance `int` but calling format() on it will return a string (True or False)
            # To prevent this from happening, we'll use the `real` numeric value instead (on int, float and bool)
            return format(value.real)
        elif _vld.is_text(value):
            try:
                return repr(str(_guids.Guid(value)))
            except (_guids.Guid.MissingGuidError, _guids.Guid.BadGuidError):
                return _tu.to_repr(value)
        raise TypeError('All values in an SQL expression must be of type str, bool, int or float')


def add_where(keyword_args: dict, where_clause: _tp.Union[str, Where], datasource: str = None):
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
            where_clause.fix_fields(datasource)
        keyword_args[WHERE_KWARG] = str(where_clause)
    elif isinstance(where_clause, str):
        keyword_args[WHERE_KWARG] = where_clause
    else:
        raise ValueError('{!r} must be a string or {} instance'.format(WHERE_KWARG, Where.__name__))
