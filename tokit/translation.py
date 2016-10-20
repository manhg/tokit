import re
import os
from collections import ChainMap, defaultdict

from tornado.template import Loader, Template, ParseError
from tornado import locale
from tokit.utils import on

SHORTCUT_RE = [
    (re.compile(rb'{\*\s*([\w\_]+)\s+(.*?)\*}', re.DOTALL), rb'{{ _("\1").format(\2) }}'),
    (re.compile(rb'{\*\s*([\w\_]+)\s*\*}', re.DOTALL),              rb'{{ _("\1") }}'),
]

def init_locale(config):
    """
    Load per-module `lang` folder CSV translations
    """
    chain = defaultdict(lambda: defaultdict(ChainMap))

    for m in config.modules_loaded:
        lang_path = os.path.join(config.root_path, m, 'lang')
        if not os.path.exists(lang_path):
            continue
        locale.load_translations(lang_path)

        # old translations is overrided by a `load` call,
        # so this is a hack to chain all mobule's translations into bigger one
        for lang, plurals in locale._translations.items():
            for plural, translation in plurals.items():
                chain[lang][plural].maps.append(translation)

    locale._translations = chain
    locale._supported_locales = frozenset(list(chain.keys()) + [locale._default_locale])


class CustomLoader(Loader):
    """
    Tornado's template preprocessor with translation shortcut.

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
