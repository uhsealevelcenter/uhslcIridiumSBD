#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""The setup script."""

from setuptools import setup, find_packages
from io import open

with open('README.md', encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst', encoding='utf-8') as history_file:
    history = history_file.read()

with open('requirements.txt', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup_requirements = []

test_requirements = [
    'pytest',
    # TODO: put package test requirements here
]

setup(
    name='iridiumSBD',
    version='0.1.0',
    description="Communication system for Iridium Short Burst Data Service.",
    long_description=readme + '\n\n' + history,
    author="Guilherme Castelão",
    author_email='guilherme@castelao.net',
    url='https://github.com/castelao/isbd',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'iridiumSBD=iridiumSBD.cli:main',
            'iridium-sbd=iridiumSBD.cli:main',
            'iridium-sbd-decode=iridiumSBD.decode.cli:main',
            'iridium-sbd-postprocess=iridiumSBD.processing.postprocess_isbd:main',
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="BSD license",
    zip_safe=False,
    keywords='isbd',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
