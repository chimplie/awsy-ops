#!/usr/bin/env python

import os

from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))
package_path = os.path.join(here, 'chops')


def readme():
    with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
        return f.read()


def version():
    with open(os.path.join(package_path, 'VERSION'), encoding='utf-8') as f:
        return f.read()


setup(
    name='chops',
    version=version(),
    description='Basic DevOps toolset for AWS and Docker we use in Chimplie',
    long_description=readme(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'DevOps :: Docker :: AWS',
    ],
    keywords='devops aws docker deploy',
    author='Mikhail Zyatin',
    author_email='mikhail.zytain@gmail.com',
    url='https://github.com/chimplie/chimplie-ops',
    license='MIT',
    packages=['chops', 'chops.templates', 'chops.plugins'],
    install_requires=[
        'markdown',
        'invoke==0.22.1',
        'python-dotenv==0.7.1',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    entry_points={
        'console_scripts': ['chops = chops:program.run']
    },
    include_package_data=True,
    zip_safe=False
)
