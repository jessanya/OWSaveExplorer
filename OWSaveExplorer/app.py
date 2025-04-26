#!/usr/bin/env python3

import asyncio
import logging
from typing import Optional

from textual.app import App, ComposeResult
from textual.events import Blur, Key
from textual.widgets import Footer, Header, Input, Label, Static

from OWSaveExplorer.widgets.gamesave import GameSaveTree
from OWSaveExplorer.widgets.optionlist import OptionList

logger = logging.getLogger('app')


class OWSaveExplorerApp(App):
    BINDINGS = [('enter', 'submit', 'Submit')]

    def __init__(self, config: dict) -> None:
        self.data = {}
        self.config = config
        super().__init__()

    def on_mount(self) -> None:
        self.hide_editbox()
        self.optionlist.container.mount(self.optionlist)
        if self.config.get('file'):
           asyncio.create_task(self.query_one('#tree')._open())

    def hide_editbox(self, event: Optional[Blur] = None) -> None:
        widget = self.query_one('#editbox')
        widget.disabled = True
        widget.styles.display = 'none'

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == 'submit':
            return self.optionlist.has_focus or self.editbox.has_focus
        return True

    async def action_submit(self) -> None:
        tree = self.query_one('#tree')
        tree.action_submit()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(markup=False)
        yield GameSaveTree(id='tree')

        class EditboxInput(Input):
            def on_blur(self, event: Blur) -> None:
                self.app.hide_editbox(event)

            def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
                # Use parent submit instead
                return action != 'submit'

            async def on_key(self, event: Key) -> None:
                logger.info('on_key(%r)', event)
                if event.key == 'escape':
                    self.blur()

        self.editbox = EditboxInput(id='editbox', select_on_focus=False)
        yield self.editbox

        self.optionlist = OptionList(Static(id='optionlist'))

        yield self.optionlist.container
        yield Footer()

    def action_show_list(self) -> None:
        self.optionlist.show()
        self.optionlist.focus()
