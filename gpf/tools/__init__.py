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
The *tools* subpackage contains a set of general classes and functions that
should make it a little easier to work with ArcGIS and ``arcpy``.

Some classes are wrappers for well-known ``arcpy`` classes,
created for a more user-friendly experience and/or better performance.
"""

import sys as _sys
from warnings import warn as _warn

import gpf.common.const as _const

_NOT_INITIALIZED = 'Not signed into Portal'


try:
    # Import the arcpy module globally
    import arcpy
except RuntimeError as e:
    if _NOT_INITIALIZED in str(e):
        _warn('Failed to obtain an ArcGIS license for the {!r} module'.format(_const.ARCPY), ImportWarning)
        arcpy = _const.EMPTY_OBJ
    else:
        raise
except ImportError:
    if _const.ARCPY not in _sys.modules:
        _warn('Python interpreter at {!r} cannot find the {!r} module'.format(_sys.executable, _const.ARCPY),
              ImportWarning)
        arcpy = _const.EMPTY_OBJ
    else:
        raise
