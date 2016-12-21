import os
from setuptools import setup
from itertools import chain

# Thanks to http://peterdowns.com/posts/first-time-with-pypi.html
tokit_version = '0.6.13'

def pack_files(directory):
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            yield os.path.join(path, filename)

extra_files = list(chain(pack_files('tokit/js'), pack_files('tokit/skeleton')))

setup(
    name='tokit',
    version=tokit_version,
    description='A kit for development with Tornado web framework',
    author='Giang Manh',
    author_email='manhgd@yahoo.com',
    url='https://github.com/manhg/tokit',
    download_url='https://github.com/manhg/tokit/tarball/' + tokit_version,
    keywords=['tornado', 'web', 'tokit'],
    install_requires = [
        "tornado==4.4",
        "shortuuid==0.4.3",
        "cerberus==1.0.1"
    ],
    packages=['tokit'],
    package_data={
        '': extra_files
    },
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
