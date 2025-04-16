#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import functools
from typing import Optional
from textual import on, work, events
from textual.binding import Binding
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Label, Button, Tree, Input
from rich.text import Text
from textual.widgets.tree import TreeNode
from textual_fspicker import FileOpen, FileSave

import dataclasses
import logging

logger = logging.getLogger('app')

from .logtree import LogTree 
from .savefile import SaveFile, Condition, Entry, Tristate
from .util import cmp, entry_to_markup
from .strings import rumors, signals, frequencies

class OWSaveEditorApp(App):
    BINDINGS = [('o', 'open', 'Open'),
                ('S', 'save', 'Save'),
                ('e', 'edit', 'Edit'),
                ('t', 'toggle', 'Toggle'),
                ('s', 'sort("reveal")', 'Sort (Reveal Order)'),
                ('s', 'sort("alpha")', 'Sort (Alphabetical)'),
                ]

    def __init__(self, config):
        self.data = {}
        self.config = config
        self.savefile = config.get('file', None)
        self.selected = None
        self.fact_tree = None
        super().__init__()

    def on_mount(self) -> None:
        self.load_save(self.savefile)
        self.query_one(Input).disabled = True
        self.query_one(Input).styles.display = 'none'

    def on_input_blur(self, event):
        self.query_one(Input).disabled = True
        self.query_one(Input).styles.display = 'none'

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:  
        if self.savefile and action == 'open':
            return False

        if self.selected and self.selected.data:
            if action == 'edit':
                return self.selected.data['type'] in (str, int, float)
            elif action == 'toggle':
                return self.selected.data['type'] == bool
            elif action == 'test' and self.fact_tree:
                #  logger.debug(f'{fact_tree} | {self.selected.data.get('LogFact', None)!r} | {self.selected.parent.data.get('LogFact', None) if self.selected.parent else None!r}')
                #  logger.debug(f'{self.selected.parent is not None and self.selected.parent.data.get('LogFact', None) == fact_tree}')
                #  logger.debug(f'{id(self.selected.parent) if self.selected.parent else None} | {id(self.selected.parent.data.get('LogFact', None)) if self.selected.parent and self.selected.parent.data.get('LogFact', None) else None} | {id(fact_tree)}')
                #  return self.selected.data.get('LogFact', None) == fact_tree or (self.selected.parent and self.selected.parent.data.get('LogFact', None) == fact_tree)
                return self.selected.data.get('logfact', False)
            elif action == 'sort':
                return self.fact_tree.show_binding(parameters[0])

        return True

    def load_save(self, savefile):
        self.savefile = savefile
        if not savefile:
            return
        tree = self.query_one(Tree)
        self.save = SaveFile(savefile)
        self.load_json(tree.root, self.save.data)
        tree.root.expand()
        self.query_one(Label).update(f'Loaded {savefile!r}')

    def on_tree_node_highlighted(self, event: Tree.NodeSelected):
        #  self.query_one(Label).update(f'{event.node.label} | {str(event.node.data)}')
        self.selected = event.node
        self.refresh_bindings()


    def load_json(self, node: TreeNode, json_data: object) -> None:
        logger.debug('load_json()')

        def add_node(name: str, node: TreeNode, data: object, path: Optional[list[str]]=None, parent=None) -> None:
            if node.data is None:
                node.data = {}
            if name == 'shipLogFactSaves':
                self.fact_tree = LogTree(self, node)

            path = [] if path is None else path

            t = None
            text = None
            if isinstance(data, dict):
                text = name
                if path and path[-1] == 'shipLogFactSaves':
                    color = ''
                    text = name
                    if data['revealOrder'] == -1:
                        color = '#ff0000'
                        text = Text.from_markup(f'[{color}]{name}[/]')
                    text = Text.assemble(text, f' | {rumors[name]}')
                node.set_label(Text.assemble('{} ', text))
                for key, value in sorted(data.items(), key=functools.cmp_to_key(cmp)):
                    new_node = node.add('')
                    new_node.data = {}
                    if name == 'shipLogFactSaves':
                        new_node.data['LogFact'] = True
                        logger.debug(id(new_node))
                    add_node(key, new_node, value, path + [name], node)
            elif isinstance(data, list):
                node.set_label(Text(f'[] {name}'))
                for index, value in enumerate(data):
                    new_node = node.add('')
                    add_node(str(index), new_node, value, path + [name], node)
            else:
                node.allow_expand = False
                text = name
                if path[-1] == 'knownSignals':
                    text = f'{signals[name]}({name})'
                elif path[-1] == 'knownFrequencies':
                    text = f'{frequencies.get(name, name)}({name})'

                t = type(data)
                if isinstance(data, Entry):
                    label = data.get_label()
                else:
                    label = entry_to_markup(text, data)
                if isinstance(data, Entry):
                    t = data.get_type()

                node.set_label(label)
            node.data.update({'name': name, 'text': text, 'path': path + [name], 'type': t, 'parent': parent, 'logfact': 'shipLogFactSaves' in (path[-1] if path else None, name)})

        add_node('Root', node, json_data)


    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(markup=False)
        yield Tree('Root', id='tree')
        this = self
        class MyInput(Input):
            def on_blur(self, event):
                this.on_input_blur(event)
        yield MyInput(id='input', select_on_focus=False)
        yield Footer()

    def action_open(self) -> None:
        self.run_worker(self._open())

    async def _open(self):
        if opened := await self.push_screen_wait(FileOpen()):
            #  self.query_one(Label).update(str(opened))
            self.load_save(str(opened))
        self.refresh_bindings()

    def action_save(self): 
        logger.debug('action_save()')
        self.run_worker(self._save())

    async def _save(self):
        logger.debug('_save()')
        file = self.config.get('outfile', None)
        if not file:
            file = await self.push_screen_wait(FileSave())
        if file:
            self.save.save(str(file))

    def action_toggle(self):
        if not self.selected or not self.selected.data:
            return
        path = self.selected.data['path']
        entry = self.save.get(path)
        self.query_one(Label).update(f'{path} -> {entry}')
        #  new_value = not new_value
        if entry is not None:
            if isinstance(entry, Tristate):
                entry.toggle()
            else:
                entry.set(not entry.value)
            self.selected.set_label(entry.get_label())

    async def action_sort(self, sort_type):
        if not self.fact_tree:
            return

        logger.debug(self._bindings)

        logger.debug('Removing')
        tree = self.query_one(Tree)

        self.fact_tree.sort(sort_type)

        selected = self.selected
        if selected.data.get('logfact', False) or (self.selected.parent and self.selected.parent.data.get('logfact', False)):
            #  logger.debug(f'{selected._line} | {tree.scroll_y}')
            tree.scroll_to_node(selected)
            #  logger.debug(f'{selected._line} | {tree.scroll_y}')

            line = selected._line
            visible = tree.size.height
            tree.scroll_y = max(line - visible // 2, 0)

    def action_edit(self):
        if not self.selected or not self.selected.data:
            return

        if self.selected.data['type'] == bool:
            return

        widget = self.query_one(Input)
        widget.disabled = False
        widget.styles.display = 'block'
        widget.value = str(self.save.get_value(self.selected.data['path']))
        float_regex = r'^-?[0-9]*(?:\.[0-9]*)$'
        int_regex = r'^-?[0-9]*$'

        if re.match(float_regex, widget.value):
            widget.type = 'numeric'
            widget.restrict = float_regex
        elif re.match(int_regex, widget.value):
            widget.type = 'integer'
            widget.restrict = int_regex
        else:
            widget.type = 'text'
            widget.restrict = None

        widget.focus()

    async def on_click(self, event) -> None:
        if event.widget.id == 'tree' and event.chain==2:
            self.action_edit()


