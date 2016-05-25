from setuptools import setup

# Thanks to http://peterdowns.com/posts/first-time-with-pypi.html
tokit_version = '0.5.4'

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
    install_requires = [
        "tornado==4.3"
    ],
    classifiers=[
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
