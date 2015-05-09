from distutils.core import setup
# Thanks to http://peterdowns.com/posts/first-time-with-pypi.html
setup(
    name = 'tokit',
    packages = ['tokit'],
    version = '0.1.3',
    description = r'''A kit for development with Tornado web framework.
        'See https://github.com/manhg/writekit for usage demo.''',
    author = 'Giang Manh',
    author_email = 'manhgd@yahoo.com',
    url = 'https://github.com/manhg/tokit',
    download_url = 'https://github.com/manhg/tokit/tarball/0.1.1',
    keywords = ['tornado', 'web'],
    classifiers=[
        'Programming Language :: Python :: 3.4',
        ],
)
