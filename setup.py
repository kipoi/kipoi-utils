#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

requirements = [
    "pandas>=0.21.0",
    "tqdm",
    "attrs>=17.4.0",
    "related>=0.6.0",
    "six",
    "tqdm",
    "numpy"
]

test_requirements = [
    "bumpversion",
    "wheel",
    "pytest>=3.3.1",
    "pytest-xdist",  # running tests in parallel
    "pytest-pep8",  # see https://github.com/kipoi/kipoi/issues/91
    "pytest-cov",
    "coveralls",  
]

setup(
    name='kipoi_utils',
    version='0.1.0',
    description="kipoiutils: utils used in various packages related to kipoi",
    author="Kipoi team",
    author_email='thorsten.beier@embl.de',
    url='https://github.com/kipoi/kipoiutils',
    long_description="kipoiutils: sequence-based data-laoders for Kipoi",
    packages=find_packages(),
    install_requires=requirements,
    extras_require={
        "develop": test_requirements,
    },
    license="MIT license",
    zip_safe=False,
    keywords=["model zoo", "deep learning",
              "computational biology", "bioinformatics", "genomics"],
    test_suite='tests',
    include_package_data=False,
    tests_require=test_requirements
)
