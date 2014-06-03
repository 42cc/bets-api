#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os.path import join, dirname
from setuptools import setup, find_packages


def get_version(fname='bets/__init__.py'):
    with open(fname) as f:
        for line in f:
            if line.startswith('__version__'):
                return eval(line.split('=')[-1])

setup(
    name='bets-api',
    version=get_version(),
    packages=find_packages(),
    requires=['python (>= 2.7)', ],
    install_requires=[
        'gevent >= 1.0.1',
        'requests >= 2.2.1',
    ],
    tests_require=[],
    description='A wrapper over bets.42cc.co API',
    long_description=open(join(dirname(__file__), 'README.rst')).read(),
    author='42 Coffee Cups',
    author_email='contact@42cc.co',
    url='https://github.com/42cc/bets-api',
    download_url='https://github.com/42cc/bets-api/archive/master.zip',
    license='GPL v2 License',
    keywords=['bets', 'api'],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python',
    ],
)
