# Copyright (c) 2016, Isotoma Limited
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Isotoma Limited nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL ISOTOMA LIMITED BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import absolute_import, unicode_literals

import json
from copy import deepcopy

from django.forms import widgets
from django.utils import translation
from wagtail.utils.widgets import WidgetWithScript

from wagtail import __version__ as WAGTAIL_VERSION

if WAGTAIL_VERSION >= '2.0':
    from wagtail.admin.edit_handlers import RichTextFieldPanel
    from wagtail.admin.rich_text.converters.editor_html import EditorHTMLConverter
    from wagtail.core.rich_text import features
else:
    from wagtail.wagtailadmin.edit_handlers import RichTextFieldPanel
    from wagtail.wagtailcore.rich_text import DbWhitelister
    from wagtail.wagtailcore.rich_text import expand_db_html

DEFAULT_BUTTONS = [
    [
        ['undo', 'redo'],
        ['styleselect'],
        ['bold', 'italic'],
        ['bullist', 'numlist', 'outdent', 'indent'],
        ['table'],
        ['link', 'unlink'],
        ['wagtaildoclink', 'wagtailimage', 'wagtailembed'],
        ['pastetext', 'fullscreen'],
    ],
]

DEFAULT_OPTIONS = {
    'browser_spellcheck': True,
    'noneditable_leave_contenteditable': True,
    'language_load': True,
}


class TinyMCERichTextArea(WidgetWithScript, widgets.Textarea):
    #: The function to call to initialize the text area.
    #: Overridable to allow deeper customization.
    tinymce_js_initializer = 'makeTinyMCEEditable'
    default_buttons = DEFAULT_BUTTONS
    default_options = DEFAULT_OPTIONS

    def __init__(self, attrs=None, buttons=None, menus=False, options=None, **kwargs):
        """
        :param attrs: HTML field attributes
        :type attrs: dict|None
        :param buttons: Toolbar button configuration. List of lists (rows) of lists (groups) of strings (buttons).
                        Best explained by `DEFAULT_BUTTONS`.  Defaults to the class's `default_buttons`.
        :type buttons: list[list[list[str]]]
        :param menus: Whether or not the menubar should be enabled, and if yes, what menus should be shown.
                      If None, the default TinyMCE configuration is used; if exactly False, menus are disabled.
                      Otherwise this is expected to be a list of strings (menu ids).
        :type menus: list[str]|bool|None
        :param options: Bag of other TinyMCE options; overlaid on top of the class's `default_options`.
        :type options: dict[str, object]
        """
        super(TinyMCERichTextArea, self).__init__(attrs)
        self.features = kwargs.pop('features', None)

        if WAGTAIL_VERSION >= '2.0':
            if self.features is None:
                self.features = features.get_default_features()
                self.converter = EditorHTMLConverter()
            else:
                self.converter = EditorHTMLConverter(self.features)

        if buttons is None:
            buttons = deepcopy(self.default_buttons)
        self.tinymce_buttons = buttons
        self.tinymce_menus = menus
        self.tinymce_options = self.default_options.copy()
        self.tinymce_options.update((options or {}))

    def get_panel(self):
        return RichTextFieldPanel

    def render(self, name, value, attrs=None):
        if value is None:
            translated_value = None
        else:
            if WAGTAIL_VERSION >= '2.0':
                translated_value = self.converter.from_database_format(value)
            else:
                translated_value = expand_db_html(value, for_editor=True)
        return super(TinyMCERichTextArea, self).render(name, translated_value, attrs)

    def render_js_init(self, id_, name, value):
        return "{0}({1}, {2});".format(
            self.tinymce_js_initializer,
            json.dumps(id_),
            json.dumps(self.build_js_init_arguments()),
        )

    def build_js_init_arguments(self):
        """
        Build the arguments written into the `makeTinyMCEEditable` JavaScript call.
        These end up (slightly mangled; please see the source for the JS function)
        as the option object for the `tinymce.init` call.
        :return: dict of JSON-able data
        :rtype: dict
        """
        kwargs = dict(
            self.tinymce_options,
            language=translation.to_locale(translation.get_language()),
            toolbar=False,
        )
        if self.tinymce_buttons:
            kwargs['toolbar'] = [
                ' | '.join([' '.join(groups) for groups in rows])
                for rows in self.tinymce_buttons
            ]
        if self.tinymce_menus is False:
            kwargs['menubar'] = False
        elif self.tinymce_menus:
            kwargs['menubar'] = ' '.join(self.tinymce_menus)
        return kwargs

    def value_from_datadict(self, data, files, name):
        original_value = super(TinyMCERichTextArea, self).value_from_datadict(data, files, name)
        if original_value is None:
            return None

        if WAGTAIL_VERSION >= '2.0':
            return self.converter.to_database_format(original_value)
        else:
            return DbWhitelister.clean(original_value)