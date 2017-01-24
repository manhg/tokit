import os
import sys

try:
    from better import better_theme_path

    html_theme_path = [better_theme_path]
    html_theme = 'better'
except ImportError:
    html_theme = 'bizstyle'

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

master_doc = "index"
project = "tokit"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks"
]

autodoc_member_order = "bysource"
autodoc_default_flags = ['members', 'undoc-members', 'private-members']
autoclass_content = "both"

# Without this line sphinx includes a copy of object.__init__'s docstring
# on any class that doesn't define __init__.
# https://bitbucket.org/birkenfeld/sphinx/issue/1337/autoclass_content-both-uses-object__init__
autodoc_docstring_signature = False
coverage_skip_undoc_in_source = True
coverage_ignore_classes = []