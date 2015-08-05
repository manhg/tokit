#!/usr/bin/env python
from tofab import *

env.x.app = 'PR0JECT'
env.hosts = ['PR0JECT.com']
env.x.base_port = 7380
env.x.n_instances = 2
env.x.remote_path = '/home/PR0JECT'
env.x.wait = 3 # (second) time wait for loading complete
env.user = env.x.app
env.port = 9622
