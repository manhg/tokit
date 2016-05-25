# Quickly setup a project skeleton

import os
import shutil
import subprocess

from .api import secret


def create_project(name):
    print("This will create a project skeleton using Tokit in current directory")
    source = os.path.join(os.path.dirname(__file__), 'skeleton')
    destination = os.path.join(os.getcwd(), name)
    print("Destination: ", destination)
    shutil.copytree(source, destination)

    commands = [
        "cd %s" % destination,
        """LC_ALL=C find config -name '*.*' -type f \
            -exec sed -i '' s/PR0JECT/%s/g {} \; """ % name,

        'cp config/development.sample.ini config/development.ini',
        'cp config/production.sample.ini config/production.ini',
        'echo "\n[secret]\ncookie_secret=%s\n" >> config/production.ini' % secret(),

        "pyvenv . ",
        "source bin/activate",
        "pip3 install -r src/requirements.txt"
        "python3 src/app.py"
    ]

    subprocess.call('; '.join(commands), stderr=subprocess.STDOUT, shell=True)

if __name__ == '__main__':

    name = input("Enter project name (empty to quit): ")
    if name:
        create_project(name)
