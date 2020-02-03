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

import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


tests_require = ['pytest', 'pytest-cov', 'mock', 'pytest-mock']
setup(
        name='gpf3',
        packages=find_packages(exclude=('tests', 'docs')),
        use_scm_version=True,
        setup_requires=['setuptools_scm'],
        license='Apache License 2.0',
        description='Geocom Python Framework for ArcPy (Esri ArcGIS Pro).',
        long_description_content_type='text/x-rst',
        long_description=read('README.rst'),
        author='Geocom Informatik AG / VertiGIS, Burgdorf, Switzerland',
        author_email='github@geocom.ch',
        url='https://github.com/geocom-gis/gpf3',
        project_urls={
            'Source': 'https://github.com/geocom-gis/gpf3',
            'Documentation': 'https://gpf3.readthedocs.io/'
        },
        keywords=[
            'Geocom', 'GIS', 'GEONIS', 'tools', 'scripting', 'framework', 'spatial',
            'geospatial', 'geoprocessing', 'Esri', 'ArcGIS', 'ArcPy', 'VertiGIS'
        ],
        python_requires='>=3.6',
        tests_require=tests_require,
        extras_require={
            'test': tests_require
        },
        classifiers=[
            'Development Status :: 4 - Beta',  # "3 - Alpha", "4 - Beta" or "5 - Production/Stable"
            'Intended Audience :: Developers',
            'Environment :: Other Environment',
            'Operating System :: Microsoft :: Windows',
            'Topic :: Scientific/Engineering :: GIS',
            'License :: OSI Approved :: Apache Software License',
            'Programming Language :: Python :: 3.6'
        ]
)
