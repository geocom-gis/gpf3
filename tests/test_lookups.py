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

from gpf.lookups import get_nodekey


def test_coord_key():
    coord = (4.2452, 23.24541)
    assert get_nodekey(*coord) == (42451, 232454)
    assert get_nodekey(53546343.334242254, 23542233.354352246) == (535463433342, 235422333543)
    assert get_nodekey(1, 2, 3) == (10000, 20000, 30000)
