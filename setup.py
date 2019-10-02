# coding: utf-8

#  Copyright (c) 2019 | Geocom Informatik AG, Burgdorf, Switzerland | MIT License

from distutils.core import setup

setup(
        name='geocom3',
        packages=['geocom'],
        version='0.1',
        license='MIT',
        description='Scripting framework for ArcPy (ArcGIS Pro 2.2+).',
        author='Geocom Informatik AG, Burgdorf, Switzerland',
        author_email='github@geocom.ch',
        # url='https://github.com/user/reponame',  # TODO
        # download_url='https://github.com/user/reponame/archive/v_01.tar.gz',  # TODO
        requires=['pytest'],
        keywords=[
            'Geocom', 'GIS', 'GEONIS', 'tools', 'scripting', 'framework', 'spatial',
            'geospatial', 'geoprocessing', 'Esri', 'ArcGIS', 'ArcPy'
        ],
        classifiers=[
            'Development Status :: 4 - Beta',  # "3 - Alpha", "4 - Beta" or "5 - Production/Stable"
            'Intended Audience :: Developers',
            'Environment :: Other Environment',
            'Operating System :: Microsoft :: Windows',
            'Topic :: Scientific/Engineering :: GIS',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3.6',
        ]
)
