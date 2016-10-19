from setuptools import setup

# Thanks to http://peterdowns.com/posts/first-time-with-pypi.html
tokit_version = '0.6.9'

setup(
    name='tokit',
    packages=['tokit'],
    version=tokit_version,
    description='A kit for development with Tornado web framework',
    author='Giang Manh',
    author_email='manhgd@yahoo.com',
    url='https://github.com/manhg/tokit',
    download_url='https://github.com/manhg/tokit/tarball/' + tokit_version,
    keywords=['tornado', 'web', 'tokit'],
    install_requires = [
        "tornado>=4.3",
        "shortuuid"
    ],
    package_data={'tokit': [
        'js/*.js', 'skeleton/*',
        'skeleton/config/*', 'skeleton/src/*', 'skeleton/src/home/*'
    ]},
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
