#!/usr/bin/env python3

import logging
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.events import Blur
from textual.widgets import Footer, Header, Input, Label
from textual_fspicker import FileOpen, FileSave

from OWSaveExplorer.gamesave import GameSave
from OWSaveExplorer.widgets.gamesave import GameSaveWidget

logger = logging.getLogger('app')

class OWSaveExplorerApp(App):
    BINDINGS = [
        ('o', 'open', 'Open'),
        ('S', 'save', 'Save'),
    ]

    def __init__(self, config: dict) -> None:
        self.data = {}
        self.config = config
        self.savefile = config.get('file')
        self.selected = None
        self.fact_tree = None
        super().__init__()

    def on_mount(self) -> None:
        self.load_save(self.savefile)
        self.hide_editbox()

    def hide_editbox(self, event: Optional[Blur]=None) -> None:
        widget = self.query_one('#editbox')
        widget.disabled = True
        widget.styles.display = 'none'

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.savefile and action == 'open':
            return False

        if self.savefile and action == 'save':
            return True

        return True

    def load_save(self, savefile: str) -> None:
        self.savefile = savefile
        if not savefile:
            return
        tree = self.query_one('#tree')
        with Path(savefile).open() as file:
            self.save = GameSave.from_json(file)
        tree.set_gamesave(self.save)
        #  self.load_json(tree.root, self.save.data)
        tree.root.expand()
        self.query_one(Label).update(f'Loaded {savefile!r}')

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(markup=False)
        #  yield Tree('Root', id='tree')
        yield GameSaveWidget(id='tree')
        this = self

        class MyInput(Input):
            def on_blur(self, event: Blur) -> None:
                this.hide_editbox(event)

            async def action_submit(self) -> None:
                tree = this.query_one('#tree')
                tree.edit(self.value)

        yield MyInput(id='editbox', select_on_focus=False)
        yield Footer()

    def action_open(self) -> None:
        self.run_worker(self._open())

    async def _open(self) -> None:
        if opened := await self.push_screen_wait(FileOpen()):
            self.load_save(str(opened))
        self.refresh_bindings()

    def action_save(self) -> None:
        logger.debug('action_save()')
        self.run_worker(self._save())

    async def _save(self) -> None:
        logger.debug('_save()')
        file = self.config.get('outfile', None)
        if not file:
            file = await self.push_screen_wait(FileSave())
        # if file:
        #     self.save.save(str(file))
