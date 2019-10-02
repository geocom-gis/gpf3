# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

import pytest

from geocom.common import containers


# noinspection PyTypeChecker
def test_bad_init():
    with pytest.raises(TypeError):
        containers.BucketFactory()
    with pytest.raises(ValueError):
        containers.BucketFactory('4you')
        containers.BucketFactory('__getattr__')
        containers.BucketFactory(1)
        containers.BucketFactory('a', 'a')


def test_buckets():
    fields = ['a', 'b', 'c']
    bucket_factory = containers.BucketFactory(fields)

    # Test Bucket
    bucket_class = bucket_factory.get_bucket_class()
    bucket = bucket_class(1, 2, 3)
    assert repr(bucket) == 'Bucket(a=1, b=2, c=3)'
    with pytest.raises(AttributeError):
        bucket.d = 4
    bucket.c = 5
    assert repr(bucket) == 'Bucket(a=1, b=2, c=5)'

    # Test FrozenBucket
    bucket_class = bucket_factory.get_bucket_class(False)
    bucket = bucket_class(1, 2, 3)
    assert repr(bucket) == 'FrozenBucket(a=1, b=2, c=3)'
    with pytest.raises(AttributeError):
        bucket.d = 4
        bucket.c = 5

    # Test factory function
    fields = ['TEST', 'Attribute', 'That\'s special!']
    bucket_class = containers.get_bucket_class(fields)
    bucket = bucket_class(1, 2, 3)
    assert bucket._fields == ('test', 'attribute', 'that_s_special')
    assert repr(bucket) == 'Bucket(test=1, attribute=2, that_s_special=3)'
