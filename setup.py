from distutils.core import setup

# Thanks to http://peterdowns.com/posts/first-time-with-pypi.html
tokit_version = '0.4.0'
setup(
    name='tokit',
    packages=['tokit'],
    version=tokit_version,
    description=r'''A kit for development with Tornado web framework.
        'See https://github.com/manhg/writekit for usage demo.''',
    author='Giang Manh',
    author_email='manhgd@yahoo.com',
    url='https://github.com/manhg/tokit',
    download_url='https://github.com/manhg/tokit/tarball/' + tokit_version,
    keywords=['tornado', 'web', 'tokit'],
    classifiers=[
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    install_requires=[
        'tornado',
        # 'cassandra-driver',
        # 'momoko',
    ],
    dependency_links=[
        # 'https://github.com/tornadoweb/tornado/archive/v4.2.1.tar.gz',
        # 'https://github.com/FSX/momoko/archive/v2.2.0.tar.gz',
        # 'https://github.com/datastax/python-driver/archive/2.7.2.tar.gz',
    ],
)
