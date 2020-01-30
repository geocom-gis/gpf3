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

# noinspection PyUnresolvedReferences
"""
The **validate** module can be used to verify if certain values are "truthy".
Most of the functions in this module return a **boolean** (True/False).

Exceptions to this rule are the :func:`pass_if` and :func:`raise_if` functions, which can be used for data assertions
and therefore serve as an alternative to the ``assert`` statement (which should not be used in production environments).

    >>> def test(text):
    >>>     pass_if(isinstance(text, str), TypeError, 'test() requires text input')
    >>>     print(text)
    >>>
    >>> test('Hello World')
    'Hello World'
    >>>
    >>> test(123)
    Traceback (most recent call last):
      File "<input>", line 1, in <module>
    TypeError: test() requires text input
"""

import inspect as _inspect
import typing as _tp
from numbers import Number as _Number

import gpf.common.const as _const
import gpf.common.guids as _guids


def is_text(value: _tp.Any, allow_empty: bool = True) -> bool:
    """
    Returns ``True`` if **value** is a ``str`` instance.

    :param value:       The value to check.
    :param allow_empty: If ``True`` (default), empty string values are allowed.
                        If ``False``, empty strings will evaluate as "falsy".
    """
    if isinstance(value, str):
        return allow_empty or value != _const.CHAR_EMPTY
    return False


def is_number(value: _tp.Any, allow_bool: bool = False) -> bool:
    """
    Returns ``True`` if *value* is a built-in numeric object (e.g. ``int``, ``float``, ``long``, ``Decimal``, etc.).

    Note that :func:`is_number` will return ``False`` for booleans by default, which is non-standard behaviour,
    because ``bool`` is a subclass of ``int``:

        >>> isinstance(True, int)
        True
        >>> is_number(True)
        False

    :param value:       The value to check.
    :param allow_bool:  If the standard Python boolean evaluation behavior is desired, set this to ``True``.
    """
    if isinstance(value, bool):
        return allow_bool
    return isinstance(value, _Number)


def is_iterable(value: _tp.Any) -> bool:
    # noinspection PyUnresolvedReferences
    """
    Returns ``True`` if *value* is an iterable container (e.g. ``list`` or ``tuple`` but not a **generator**).

    Note that :func:`is_iterable` will return ``False`` for string-like objects as well, even though they are iterable.
    The same applies to **generators** and **sets**:

        >>> my_list = [1, 2, 3]
        >>> is_iterable(my_list)
        True
        >>> is_iterable(set(my_list))
        False
        >>> is_iterable(v for v in my_list)
        False
        >>> is_iterable(str(my_list))
        False

    :param value:   The value to check.
    """
    return not isinstance(value, str) and hasattr(value, '__iter__') and hasattr(value, '__getitem__')


def is_guid(value: _tp.Any) -> bool:
    """
    Returns ``True`` when the given *value* is a GUID-like object and ``False`` otherwise.
    The function effectively tries to parse the value as a :class:`gpf.tools.guids.Guid` object.

    :param value:   A string or a GUID-like object.
    """
    try:
        _guids.Guid(value)
    except (_guids.Guid.BadGuidError, _guids.Guid.MissingGuidError):
        return False
    return True


def has_value(obj: _tp.Any, strip: bool = False) -> bool:
    """
    Returns ``True`` when *obj* is "truthy".

    Note that :func:`has_value` will return ``True`` for the ``False`` boolean and ``0`` integer values.
    Python normally evaluates these values as "falsy", but for databases for example, these values are perfectly valid.
    This is why :func:`has_value` considers them to be "truthy":

        >>> my_int = 0
        >>> my_bool = False
        >>> if not (my_int and my_bool):
        >>>     print('Both values are "falsy".')
        'Both values are "falsy".'
        >>> has_value(my_int)
        True
        >>> has_value(my_bool)
        True

    Other usage examples:

        >>> has_value(None)
        False
        >>> has_value({})
        False
        >>> has_value('test')
        True
        >>> has_value('   ', strip=True)
        False

    :param obj:     The object for which to evaluate its value.
    :param strip:   If ``True`` and *obj* is a ``str``, *obj* will be stripped before evaluation. Defaults to ``False``.
    """
    if not obj:
        return obj == 0
    if is_text(obj):
        return (obj.strip() if strip else obj) != _const.CHAR_EMPTY
    return True


def signature_matches(func: _tp.Callable, template_func: _tp.Callable) -> bool:
    """
    Checks if the given *func* (`function` or `instancemethod`) has a signature equal to *template_func*.
    If the function is not callable or the signature does not match, ``False`` is returned.

    :param func:            A callable function or (instance) method.
    :param template_func:   A template function to which the callable function argument count should be compared.
                            This should *not* be a an instance method.
    :rtype:                 bool
    """

    def _get_params(f):
        """ Returns the Parameter objects for a function (skipping 'self', if present). """
        try:
            sig = _inspect.signature(f)
        except (ValueError, TypeError):
            params = _inspect.OrderedDict()
        else:
            params = sig.parameters or _inspect.OrderedDict()
        for i, (name, p) in enumerate(params.items()):
            if i == 0 and name == 'self':
                # For instance methods/functions, we'll remove the first parameter ("self" by convention)
                continue
            yield p

    if not callable(func) or not callable(template_func):
        return False
    # Compare the parameter count, names and types
    return tuple(_get_params(func)) == tuple(_get_params(template_func))


def pass_if(expression: _tp.Any, exc_type: type(Exception), exc_val: _tp.Any = _const.CHAR_EMPTY) -> bool:
    """
    Raises an error of type *err_type* when *expression* is **falsy** and silently passes otherwise.
    Opposite of :func:`raise_if`.

    :param expression:  An expression or value to evaluate.
    :param exc_type:    The error to raise when *expression* evaluates to ``False``, e.g. ``AttributeError``.
    :param exc_val:     An optional message or exception value to include with the error (recommended).

    :Examples:

        >>> my_value = 0
        >>> pass_if(my_value)
        Traceback (most recent call last):
          File "<input>", line 1, in <module>
        AssertionError
        >>> pass_if(my_value == 0)
        >>> pass_if(my_value == 1, ValueError, 'my_value should be 1')
        Traceback (most recent call last):
          File "<input>", line 1, in <module>
        ValueError: my_value should be 1
    """
    if not expression:
        raise exc_type(exc_val)
    return True


def raise_if(expression: _tp.Any, exc_type: type(Exception), exc_val: _tp.Any = _const.CHAR_EMPTY) -> bool:
    """
    Raises an error of type *err_type* when *expression* is **truthy** and silently passes otherwise.
    Opposite of :func:`pass_if`.

    :param expression:  An expression or value to evaluate.
    :param exc_type:    The error to raise when *expression* evaluates to ``True``, e.g. ``AttributeError``.
    :param exc_val:     An optional message or exception value to include with the error (recommended).

    :Examples:

        >>> my_value = 0
        >>> raise_if(my_value)
        >>> raise_if(my_value == 1)
        >>> raise_if(my_value == 0, ValueError, 'my_value should not be 0')
        Traceback (most recent call last):
          File "<input>", line 1, in <module>
        ValueError: my_value should not be 0
    """
    if expression:
        raise exc_type(exc_val)
    return True
