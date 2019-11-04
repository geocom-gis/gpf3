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

import sys

import pytest
from mock import Mock

from gpf.tools.geometry import *


@pytest.mark.skipif(isinstance(sys.modules['arcpy'], Mock), reason="arcpy is not available")
def test_getxyz():
    with pytest.raises(ValueError):
        get_xyz(1, 2, 'test')
        get_xyz('test', None, 3)
        get_xyz(1)
        get_xyz(None)
    assert get_xyz(1, 2, 3.14) == (1, 2, 3.14)
    assert get_xyz(1, 2.242) == (1, 2.242, None)
    assert get_xyz(1.05, 2.1, 5.6, 3.24) == (1.05, 2.1, 5.6)
    assert get_xyz({'x': 1, 'y': 2}) == (1, 2, None)
    assert get_xyz({'X': 1, 'Y': 2, 'z': 3}) == (1, 2, 3)
