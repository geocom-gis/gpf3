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

import uuid

import pytest

from gpf.common.guids import Guid


def test_guid_bad():
    with pytest.raises(Guid.MissingGuidError):
        Guid()
    with pytest.raises(Guid.BadGuidError):
        Guid('test')


def test_guid_ok():
    assert Guid(uuid.UUID('b2ae10b1-a540-44b9-b785-7168f7d8d22e')) == '{B2AE10B1-A540-44B9-B785-7168F7D8D22E}'
    assert Guid('b2ae10b1-a540-44b9-b785-7168f7d8d22e') == '{b2ae10b1-a540-44b9-b785-7168f7d8d22e}'
    assert str(Guid('b2ae10b1a54044b9b7857168f7d8d22e')) == '{B2AE10B1-A540-44B9-B785-7168F7D8D22E}'
    assert str(Guid('{B2AE10B1-A540-44B9-B785-7168F7D8D22E}')) == '{B2AE10B1-A540-44B9-B785-7168F7D8D22E}'
    assert isinstance(Guid(allow_new=True), uuid.UUID) is True
    assert isinstance(Guid(None, True), uuid.UUID) is True
