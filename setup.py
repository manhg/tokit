import os
from setuptools import setup
from itertools import chain

# Thanks to http://peterdowns.com/posts/first-time-with-pypi.html
tokit_version = '0.7.4'

setup(
    name='tokit',
    version=tokit_version,
    description='A kit for development with Tornado web framework',
    author='Giang Manh',
    author_email='manhgd@yahoo.com',
    url='https://github.com/manhg/tokit',
    download_url='https://github.com/manhg/tokit/tarball/' + tokit_version,
    keywords=['tornado', 'web', 'tokit'],
    packages=['tokit'],
    package_data={
        'tokit': [
            'js/*.js'
        ]
    },
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.5'
    ]
)
