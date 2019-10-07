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
Pytest configuration module.
"""

import sys
import pytest


def pytest_addoption(parser):
    # Add option to mock the arcpy module.
    # This is required on systems where ArcGIS and/or a license is not available.
    # Note that this might produce unexpected results for certain tests!
    parser.addoption('--mock_arcpy', action='store_true', help='Replace arcpy module with a mock object')


def pytest_collection(session):
    # If pytest is initialized with the --mock_arcpy option, define arcpy in sys.modules as a MagicMock object.
    # Warn the user if arcpy has been patched, so that it's clear that it will not work as expected.
    if session.config.option.mock_arcpy:
        from warnings import warn
        from mock import MagicMock

        sys.modules['arcpy'] = MagicMock()

        warn('The arcpy module has been replaced by a mock object', pytest.PytestWarning)
