# Quickly setup a project skeleton
import os
import shutil
import subprocess

if __name__ == '__main__':
    project = input("Enter project name (empty to quit): ")
    if project:
        print("This will create a project skeleton using Tokit in current directory")
        source = os.path.join(os.path.dirname(__file__), 'skeleton')
        destination = os.path.join(os.getcwd(), project)
        print("Destination: ", destination)
        shutil.copytree(source, destination)
        cmd = ("""LC_ALL=C find %s -name '*.*' -type f """ +
            """-exec sed -i '' s/PR0JECT/%s/g {} \; """) \
            % (destination, project)
        print(cmd)
        print(subprocess.call(cmd, shell=True))
