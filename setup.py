#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


requirements = [
    "pandas>=0.21.0",
    "tqdm",
    "attrs",
    "related",
    "tqdm",
    "numpy",
    "PyYAML>=5.1.0",
    #"psutil"
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
desc = "kipoi-utils: utils used in various packages related to kipoi"
setup(
    name='kipoi_utils',
    version='0.7.6',
    description=desc,
    author="Kipoi team",
    author_email='thorsten.beier@embl.de',
    url='https://github.com/kipoi/kipoi-utils',
    long_description=desc,
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
