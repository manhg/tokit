#!/usr/bin/env python
try:
    from tofab import *
except:
    print "tofab is missing"

env.x.app = 'PR0JECT'
env.hosts = ['PR0JECT.com']
env.x.base_port = 9000
env.x.n_instances = 2
env.x.remote_path = '/home/PR0JECT'
env.x.wait = 3  # (second) time wait for loading complete
env.user = env.x.app
env.port = 9622


def update_vendors():
    """
    Update frontend libraries
    """
    local("wget https://raw.githubusercontent.com/riot/riot/master/riot.js -O src/static/vendor/tag.js")
    local("wget https://raw.githubusercontent.com/github/fetch/master/fetch.js -O src/static/vendor/fetch.js")
    local("wget https://raw.githubusercontent.com/cujojs/curl/master/src/curl.js src/static/vendor/amd.js")
