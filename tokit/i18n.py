import re
import os
from tornado.template import Loader, Template


class CustomLoader(Loader):
    """
    Template preprocessor with translation shortcut.

        * ``{::key}`` -> ``{{ _("key") }}``
        * ``{:key}``-> ``{{ _(key) }}``
        * ``{=expr}``-> ``{{ expr }}``
    """

    def _custom_prepocessor(self, content):
        _content = re.sub(rb'{\:\:(.*?)}', rb'{{ _("\1") }}', content, re.DOTALL)
        _content = re.sub(rb'{\:(.*?)}', rb'{{ _(\1) }}', _content, re.DOTALL)
        _content = re.sub(rb'{=(.*?)}', rb'{{ \1 }}', _content, re.DOTALL)
        return _content

    def _create_template(self, name):
        path = os.path.join(self.root, name)
        with open(path, "rb") as f:
            template = Template(
                self._custom_prepocessor(f.read()),
                name=name, loader=self,
                compress_whitespace=False)
            return template


class I18nMixin:
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
