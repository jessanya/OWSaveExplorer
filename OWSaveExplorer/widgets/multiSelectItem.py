#!/usr/bin/env python3

import logging

from textual.widgets import Label, ListItem

logger = logging.getLogger('MultiSelectItem')

class MultiSelectItem(ListItem):
    def __init__(self, label: str, value: bool=False, radio: bool=False) -> None:
        # logger.debug('MultiSelectItem(label:%s, value:%s, radio:%s)', label, value, radio)
        self.label = label
        self.label_text = label
        self.radio = radio
        self.value = value
        self.label_widget = Label(self.render_label())
        super().__init__(self.label_widget)

    def render_label(self) -> str:
        # logger.debug(self.value)
        prefix = ('(x)' if self.value else '( )') if self.radio else ('\\[x]' if self.value else '\\[ ]')
        return f'{prefix} {self.label_text}'

    def set(self, value: bool) -> None:
        # logger.debug('set(%s) | %s | %s -> %s', value, self.label_text, self.radio, self.value)
        self.value = value
        self.label_widget.update(self.render_label())

    def toggle(self) -> None:
        # logger.debug('toggle(%s) -> %s', not self.value, self.value)
        self.value = not self.value
        self.label_widget.update(self.render_label())

