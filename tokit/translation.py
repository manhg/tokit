import re
import os
from tornado.template import Loader, Template

SHORTCUT_RE = [
    (re.compile(rb'{\:\:(.*?)}', re.DOTALL),    rb'{{ _("\1") }}'),
    (re.compile(rb'{\:(.*?)}', re.DOTALL),      rb'{{ _(\1) }}'),
    (re.compile(rb'{=(.*?)}', re.DOTALL),       rb'{{ \1 }}'),
]


class CustomLoader(Loader):
    """
    Tornado's template preprocessor with translation shortcut.
    Key must be in single line

        * ``{::key}`` -> ``{{ _("key") }}``
        * ``{:key}``-> ``{{ _(key) }}``
        * ``{=expr}``-> ``{{ expr }}``
    """

    def _custom_prepocessor(self, content):
        ret = content
        for regex, replacement in SHORTCUT_RE:
            ret = regex.sub(replacement, ret)
        return ret

    def _create_template(self, name):
        path = os.path.join(self.root, name)
        with open(path, "rb") as f:
            template = Template(
                self._custom_prepocessor(f.read()),
                name=name, loader=self,
                compress_whitespace=False)
            return template


class TranslationMixin:

    def create_template_loader(self, template_path):
        settings = self.application.settings
        if "template_loader" in settings:
            return settings["template_loader"]
        kwargs = {}
        if "autoescape" in settings:
            # autoescape=None means "no escaping", so we have to be sure
            # to only pass this kwarg if the user asked for it.
            kwargs["autoescape"] = settings["autoescape"]
        return CustomLoader(template_path, **kwargs)
