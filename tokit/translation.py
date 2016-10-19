import re
import os
from tornado.template import Loader, Template, ParseError
from tornado.locale import load_translations
from tokit.utils import on

SHORTCUT_RE = [
    (re.compile(rb'{\*\s*([\w\_]+)\s+(.*?)\*}', re.DOTALL), rb'{{ _("\1").format(\2) }}'),
    (re.compile(rb'{\*\s*([\w\_]+)\s*\*}', re.DOTALL),              rb'{{ _("\1") }}'),
]

def init_locale(config):
    for m in config.modules_loaded:
        lang_path = os.path.join(config.root_path, m, 'lang')
        if os.path.exists(lang_path):
            load_translations(lang_path)


class CustomLoader(Loader):
    """
    Tornado's template preprocessor with translation shortcut.
    Key must be in single line

        * ``{* key | name=value *}``-> ``{{ _("key").format(name=value) }}``
        * ``{* key *}``-> ``{{ _("key") }}``
    """

    def _custom_prepocessor(self, content):
        ret = content
        for regex, replacement in SHORTCUT_RE:
            ret = regex.sub(replacement, ret)
        return ret

    def _create_template(self, name):
        path = os.path.join(self.root, name)
        with open(path, "rb") as f:
            try:
                template = Template(
                    self._custom_prepocessor(f.read()),
                    name=name, loader=self,
                    compress_whitespace=False)
                return template
            except ParseError as exception:
                exception.args = exception.args + (path, )
                raise


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
