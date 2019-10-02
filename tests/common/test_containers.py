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

from gpf.common import containers


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
