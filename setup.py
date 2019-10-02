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

from distutils.core import setup

setup(
        name='gpf3',
        packages=['gpf'],
        version='0.1',
        license='Apache License 2.0',
        description='Scripting framework for ArcPy (ArcGIS Pro 2.2+).',
        author='Geocom Informatik AG / VertiGIS, Burgdorf, Switzerland',
        author_email='github@geocom.ch',
        url='https://github.com/geocom-gis/gpf3',
        download_url='https://github.com/geocom-gis/gpf3/archive/gpf3_v010.tar.gz',
        requires=['pytest'],
        keywords=[
            'Geocom', 'GIS', 'GEONIS', 'tools', 'scripting', 'framework', 'spatial',
            'geospatial', 'geoprocessing', 'Esri', 'ArcGIS', 'ArcPy', 'VertiGIS'
        ],
        classifiers=[
            'Development Status :: 4 - Beta',  # "3 - Alpha", "4 - Beta" or "5 - Production/Stable"
            'Intended Audience :: Developers',
            'Environment :: Other Environment',
            'Operating System :: Microsoft :: Windows',
            'Topic :: Scientific/Engineering :: GIS',
            'License :: OSI Approved :: Apache License 2.0',
            'Programming Language :: Python :: 3.6',
        ]
)
