import os
import shutil
import subprocess

from tokit.utils import make_rand


def create_project(name):
    print("This will create a project skeleton using Tokit in current directory. GNU sed is requied.")
    source = os.path.join(os.path.dirname(__file__), 'skeleton')
    destination = os.path.join(os.getcwd(), name)
    print("Destination: ", destination)
    shutil.copytree(source, destination)

    commands = [
        "cd " + destination,
        """LC_ALL=C find config -type f \
            -exec sed -i s/PROJECT/%s/g {} \; """ % name,
        "python3 -m venv .",
        "bin/python3 -m ensurepip",
        "pip3 install -r requirements.txt",
        "bin/python3 src/app.py"
    ]
    subprocess.call(' && '.join(commands), stderr=subprocess.STDOUT, shell=True)

if __name__ == '__main__':
    name = input("Enter project name (empty to quit): ")
    if name:
        create_project(name)
