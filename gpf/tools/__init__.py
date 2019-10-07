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

.. note::   It is recommended to import ``arcpy`` from the *tools* subpackage (``from gpf.tools import arcpy``).
            This will load the same (and unmodified) module as ``import arcpy`` would load, but it shows
            more useful error messages when the import failed.
"""

import sys as _sys

import gpf.common.const as _const

_NOT_INITIALIZED = 'Not signed into Portal'


try:
    # Import the arcpy module globally
    import arcpy
except RuntimeError as e:
    if _NOT_INITIALIZED in str(e):
        # If the "RuntimeError: Not signed into Portal" error is thrown,
        # raise an ImportError instead with a more verbose reason.
        raise ImportError(f'Failed to obtain an ArcGIS license for the {_const.ARCPY!r} module')
    # Reraise for all other RuntimeErrors
    raise
except ImportError:
    if _const.ARCPY not in _sys.modules:
        # If arcpy cannot be found in the system modules,
        # raise an ImportError that tells the user which interpreter is being used.
        # The user might have accidentally chosen a "vanilla" Python interpreter,
        # instead of the ArcGIS Python distribution.
        raise ImportError(f'Python interpreter at {_sys.executable!r} cannot find the {_const.ARCPY!r} module')
    # Reraise for other (unlikely) ImportErrors
    raise
