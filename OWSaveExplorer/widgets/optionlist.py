#!/usr/bin/env python3

import logging
from enum import Enum

from textual.containers import Container
from textual.events import Click, Key
from textual.widgets import ListView

from OWSaveExplorer.widgets.multiSelectItem import MultiSelectItem

logger = logging.getLogger('optionlist')


class OptionList(ListView):
    BINDINGS = [
        ('space', 'toggle', 'Toggle'),
        ('enter', 'submit', 'Submit'),
    ]
    DEFAULT_CSS = """
    OptionList {
        background: $surface;
        border: tall $border;
        color: $foreground;
        padding: 0 2;
        width: 100%;
        height: 10;
    }
    """

    class ModeEnum(Enum):
        MULTI = 0
        SINGLE = 1

    def __init__(self, container: Container) -> None:
        self.container = container
        self.hide()
        self._show = False
        self.mode = self.ModeEnum.MULTI

        super().__init__()

    async def on_key(self, event: Key) -> None:
        # logger.debug('on_key(%s)', event)
        if event.key == 'escape':
            self.blur()

    async def on_click(self, event: Click) -> None:
        if event.chain == 2:  # noqa
            self.action_toggle()

    def on_blur(self) -> None:
        self.hide()

    def hide(self) -> None:
        self.container.visible = False
        self.container.display = False

    def on_idle(self) -> None:
        # Ensures labels are rendered prior to showing
        if self._show:
            self.container.visible = True
            self.container.display = True
            self.focus()
            self._show = False

    def show(self) -> None:
        self._show = True

    def action_toggle(self) -> None:
        logging.debug(
            'action_toggle() | mode:%s | label:%s | %s', self.mode, self.selected.label_text, self.selected.value
        )
        if isinstance(self.selected, MultiSelectItem):
            if self.mode == self.ModeEnum.SINGLE:
                logging.debug('%s | %s', self.selected.value, bool(self.selected.value))
                if bool(self.selected.value):
                    logging.debug('already set in SINGLE mode')
                    return
                self.selected.set(True)
                for option in self.options:
                    if self.selected != option:
                        option.set(False)
            else:
                self.selected.toggle()

    async def set_options(self, options: list[MultiSelectItem | str], mode: ModeEnum = ModeEnum.MULTI) -> None:
        # logger.debug('set_options(%s)', options)
        self.options = [
            x if isinstance(x, MultiSelectItem) else MultiSelectItem(x, radio=mode == self.ModeEnum.SINGLE)
            for x in options
        ]
        self.mode = mode
        self.clear()
        await self.extend(self.options)
        self.styles.height = len(self.options) + 2

    # async def on_mount(self) -> None:
    #     logger.debug('on_mount()')

    def on_list_view_highlighted(self, event: ListView.Selected) -> None:
        # logger.debug('on_list_view_highlighted() -> %s, %s', event.item, event.item.label_text if event.item else None)
        self.selected = event.item
