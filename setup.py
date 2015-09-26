from distutils.core import setup

# Thanks to http://peterdowns.com/posts/first-time-with-pypi.html
tokit_version = '0.3.3'
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
)
