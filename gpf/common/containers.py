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
This module holds a couple of data structure types (or "containers")
that can be used to store all kinds of data in a memory-efficient and object-oriented manner.
"""

import typing as _tp
from collections import OrderedDict
from collections import namedtuple

import more_itertools as _iter

import gpf.common.textutils as _tu
import gpf.common.validate as _vld

_DUMMY = 'dummy'


def _is_equal(self, other: _tp.Any) -> bool:
    """
    Returns ``True`` when both objects have an _asdict() method and their items are equal.

    :param other:   Comparison object.
    """
    try:
        # noinspection PyProtectedMember
        return self._asdict() == other._asdict()
    except AttributeError:
        return False


class FrozenBucket(tuple):
    """
    FrozenBucket(*values, **pairs)

    Immutable container class for storing user-defined attributes (properties).
    Because ``FrozenBucket`` is a ``namedtuple``, it is very memory-efficient and can safely be used in loops.

    This class can't be instantiated directly and must be obtained via the :func:`get_bucket_class` factory function.
    Since the class is dynamically created, the user-defined properties are only exposed at runtime.

    Examples:

        >>> bucket = get_bucket_class(['a', 'b'], writable=False)  # using the factory function
        >>> bucket('test', 3.14)
        FrozenBucket(a='test', b=3.14)

        >>> bucket_factory = BucketFactory('a', 'b')               # using the BucketFactory class
        >>> bucket = bucket_factory.get_bucket_class(writable=False)
        >>> my_bucket = bucket('test', 3.14)
        >>> my_bucket.a
        test
        >>> my_bucket.b
        3.14

    .. seealso::    :class:`BucketFactory`, :class:`Bucket`
    """

    def __new__(cls, *values, **pairs):
        raise NotImplementedError('Class must be instantiated from a {!r} generated {!r} class'.
                                  format(BucketFactory.__name__, FrozenBucket.__name__))


class Bucket:
    """
    Bucket(*values, **pairs)

    Mutable container class for storing user-defined attributes (properties).
    ``Bucket`` uses ``__slots__``, which makes it relatively memory-efficient. It can safely be used in loops.
    However, if the data stored in it remains static, it's better to use a :class:`FrozenBucket` instead.

    This class can't be instantiated directly and must be obtained via the :func:`get_bucket_class` factory function.
    Since the class is dynamically created, the user-defined properties are only exposed at runtime.

    Examples:

        >>> bucket = get_bucket_class(['a', 'b'])     # using the factory function
        >>> my_bucket = bucket('test', 3.14)
        >>> my_bucket.a
        test
        >>> my_bucket.a = my_bucket.b
        >>> my_bucket.a
        3.14

        >>> bucket_factory = BucketFactory('a', 'b')   # using the BucketFactory class
        >>> bucket = bucket_factory.get_bucket_class()
        >>> bucket('test', 3.14)
        Bucket(a='test', b=3.14)

    .. seealso::    :class:`BucketFactory`, :class:`FrozenBucket`
    """

    __slots__ = ()  # Serves as template: slots are set by the BucketFactory

    def __init__(self, *values, **pairs):
        _vld.pass_if(self._fields, NotImplementedError,
                     'Class must be instantiated from a {!r} generated {!r} class'.
                     format(BucketFactory.__name__, Bucket.__name__))
        self.update(*values, **pairs)

    def __len__(self):
        return len(self._fields)

    def __repr__(self):
        """ Returns a representation of the instance. """
        f_items = (f'{name}={value!r}' for name, value in self.items())
        return f'{Bucket.__name__}({", ".join(f_items)})'

    def __iter__(self):
        """ Returns an iterator over the stored values. """
        for name in self._fields:
            yield getattr(self, name)

    __eq__ = _is_equal

    @property
    def _fields(self) -> tuple:
        """
        Alias for getting Bucket field names (slots).

        Note: method name is "protected" to shadow the method name of the :class:`FrozenBucket` namedtuple.
        """
        return self.__slots__

    def _asdict(self) -> OrderedDict:
        """
        Returns the contents of the Bucket as an ordered dictionary.

        Note: method name is "protected" to shadow the method name of the :class:`FrozenBucket` namedtuple.
        """
        return OrderedDict(self.items())

    def items(self) -> _tp.Generator[_tp.Tuple[str, _tp.Any], _tp.Any, None]:
        """
        Returns a generator of the stored key-value pairs.

        Example:

            >>> bucket = get_bucket_class(['a', 'b'])
            >>> my_bucket = bucket('test', 3.14)
            >>> for k, v in my_bucket.items():
            >>>     print(k, v)
            ('a', 'test')
            ('b', 3.14)
        """
        return ((name, getattr(self, name)) for name in self._fields)

    def update(self, *values, **pairs) -> None:
        """
        Updates all `Bucket` values using positional and/or keyword arguments.

        Example:

            >>> bucket = get_bucket_class(['a', 'b'])
            >>> my_bucket = bucket('test', 3.14)
            >>> my_bucket.update('hello', b='world')
            >>> print(my_bucket)
            Bucket(a='hello', b='world')
        """
        # _set values according to args (in __slots__ order)
        for i, value in enumerate(values):
            setattr(self, self._fields[i], value)
        # _set values according to keyword arguments
        for name, value in pairs.items():
            setattr(self, name, value)


class BucketFactory:
    """
    BucketFactory(*attributes)

    Factory class to create :class:`FrozenBucket` or :class:`Bucket` classes.

    :param attributes:  The property names to define in the :class:`FrozenBucket` or :class:`Bucket`.
                        Note that all names are transformed to lowercase and that non-alphanumeric characters are
                        replaced by underscores to ensure valid Python attribute names.

    .. seealso::    :class:`Bucket`, :class:`FrozenBucket`
    """

    def __init__(self, *attributes: _tp.Union[str, _tp.Iterable[str]]):
        self._blacklist = frozenset(dir(Bucket) + dir(namedtuple(_DUMMY, _tu.EMPTY_STR)))

        _vld.pass_if(attributes, TypeError,
                     '{!r} must be instantiated with 1 or more attribute names'.format(BucketFactory.__name__))

        self._attr_names = self._set_attrs(attributes)

    @staticmethod
    def _fix_attr(attr_name: str) -> str:
        """ Fixes the attribute name so that all special chars become underscores. First char must be alphanumeric. """
        _vld.pass_if(attr_name[0].isalpha(), ValueError, 'Bucket field names must start with a letter')
        fixed_name = _tu.EMPTY_STR.join(char if char.isalnum() else _tu.UNDERSCORE for char in attr_name)
        return fixed_name.strip(_tu.UNDERSCORE)

    def _set_attrs(self, attributes: _tp.Iterable[str]) -> _tp.Tuple[str]:
        """ Checks and fixes all attribute names. """
        out_attrs = []
        for attr_name in _iter.collapse(attributes):
            attr_name = self._fix_attr(attr_name).lower()
            _vld.raise_if(attr_name in self._blacklist, ValueError,
                          'Field name {!r} shadows built-in name'.format(attr_name))
            _vld.raise_if(attr_name in out_attrs, ValueError, 'Field names must be unique')
            out_attrs.append(attr_name)
        return tuple(out_attrs)

    @property
    def fields(self) -> _tp.Tuple[str]:
        """
        Returns the current :class:`FrozenBucket` or :class:`Bucket` attribute names in their initial order.
        """
        return tuple(self._attr_names)

    def get_bucket_class(self, writable: bool = True) -> type:
        """
        Returns a bucket class type with the *BucketFactory* input fields as predefined slots.
        For better performance, do not immediately instantiate the returned class on the same line,
        but store it in a variable first and use this as an object initializer.

        :param writable:    When ``True`` (default), a :class:`Bucket` type is returned.
                            Otherwise, a :class:`FrozenBucket` type is returned.
        """
        if writable:
            return type(Bucket.__name__, (Bucket,), {'__slots__': self._attr_names})
        ro_class = namedtuple(FrozenBucket.__name__, self._attr_names)
        ro_class.__eq__ = _is_equal
        return ro_class


def get_bucket_class(field_names: _tp.Iterable[str], writable: bool = True) -> type:
    """
    Factory function to obtain a :class:`FrozenBucket` or a :class:`Bucket` container class.

    The function instantiates a :class:`BucketFactory` and calls its `get_bucket_class` method.

    :param field_names: An iterable of field names for which to create a bucket class.
    :param writable:    If ``False`` (default = ``True``), a :class:`FrozenBucket` type will be returned.
                        By default, a :class:`Bucket` type will be returned.

    In theory, you could immediately instantiate the returned bucket class.
    This is okay for a single bucket, but considered bad practice if you do this consecutively (e.g. in a loop).
    For example, it's fine if you do this once:

        >>> my_bucket = get_bucket_class(['field1', 'field2'])(1, 2)
        >>> print(my_bucket)
        Bucket(field1=1, field2=2)

    However, if you need to reuse the bucket class to instantiate multiple buckets, this is better:

        >>> fields = ('Field-With-Dash', 'UPPERCASE_FIELD')
        >>> bucket_cls = get_bucket_class(fields, writable=False)
        >>> for i in range(3):
        >>>     print(bucket_cls(i, i+1))
        FrozenBucket(field_with_dash=0, uppercase_field=1)
        FrozenBucket(field_with_dash=1, uppercase_field=2)
        FrozenBucket(field_with_dash=2, uppercase_field=3)

    .. seealso::    :class:`BucketFactory`, :class:`Bucket`, :class:`FrozenBucket`
    """
    # Input validation
    _vld.raise_if(field_names == _tu.ASTERISK, NotImplementedError,
                  "{} does not support {!r} as 'field_names' attribute".format(get_bucket_class.__name__, _tu.ASTERISK))
    _vld.pass_if(_vld.is_iterable(field_names), TypeError, "'field_names' attribute must be an iterable")

    rec_fields = _iter.collapse(field_names, levels=1)
    return BucketFactory(rec_fields).get_bucket_class(writable)
