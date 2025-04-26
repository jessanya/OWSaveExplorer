#!/usr/bin/env python

import logging
from enum import Flag
from itertools import product
from pathlib import Path
from typing import Callable, Optional

from rich.text import Text
from textual.binding import Binding
from textual.events import Click
from textual.validation import Function
from textual.widgets import Input, Tree
from textual.widgets.tree import TreeNode
from textual_fspicker import FileOpen, FileSave

from OWSaveExplorer.enums import (
    DeathTypeEnum,
    FrequencyEnum,
    SignalEnum,
    StartupPopupsFlag,
)
from OWSaveExplorer.gamesave import GameSave, ShipLogFactSave
from OWSaveExplorer.strings import persistent_conditions, rumors
from OWSaveExplorer.util import Tristate, ValidationWrapper, color_bool, highlighter

logger = logging.getLogger('widgets.gamesave')


class Entry:
    class DisplayMode(Flag):
        PLAIN = 0
        HIGHLIGHT = 1
        REPR = 2

    def __init__(  # noqa: PLR0913
        self,
        name: str,
        value: Optional[object] = None,
        value_transformer: Optional[Callable] = None,
        base_type: Optional[type] = None,
        mode: DisplayMode = DisplayMode.HIGHLIGHT | DisplayMode.REPR,
        validator: Optional[Function] = None,
        enabled: bool = True,
    ) -> None:
        self.name = name
        self.value = value
        self.value_transformer = value_transformer if value_transformer else lambda x: x
        self.mode = mode
        self.type = base_type

        self.validator = validator
        self.enabled = enabled

    def set(self, value: object) -> None:
        self.value = value

    def get(self) -> object:
        return self.value

    def get_label(self) -> Text:
        color_prefix = color_suffix = ''

        value = self.value_transformer(self.value)

        if isinstance(value, bool):
            value_text = color_bool(value)
        elif value is None:
            value_text = Text.from_markup(f'[yellow]{value}[/]')
        else:
            s = repr(value) if self.mode & self.DisplayMode.REPR else value
            value_text = highlighter(s) if self.mode & self.DisplayMode.HIGHLIGHT else str(s)

        if not self.enabled:
            color_prefix += 'strike'

        if color_prefix:
            color_prefix = f'[{color_prefix}]'
            color_suffix = '[/]'

        return Text.assemble(
            Text.from_markup(f'{color_prefix}[b]{self.name}[/b]{color_suffix}='),
            value_text,
        )

    def __repr__(self) -> str:
        return f'Entry(name={self.name!r}, value={self.value!r}, type={self.type!r})'

    def get_color(self) -> Optional[str]:
        return None

    def get_type(self) -> type:
        return type(self.value)


class EntryTristate(Entry):
    def __init__(self, *args, **kwargs) -> None:
        self.value: Tristate
        super().__init__(*args, value_transformer=lambda x: x.value, base_type=Tristate, **kwargs)

    def get_color(self) -> str:
        return {False: 'red', True: 'green', None: 'yellow'}[self.value.value]


class EntryBool(Entry):
    def __init__(self, *args, **kwargs) -> None:
        self.value = False
        super().__init__(*args, base_type=bool, **kwargs)

    def get_color(self) -> str:
        return {False: 'red', True: 'green'}[self.value]


class EntrySaveLogFact(Entry):
    def __init__(self, *args, **kwargs) -> str:
        self.value: ShipLogFactSave
        super().__init__(*args, **kwargs, base_type=ShipLogFactSave)

    def get_label(self) -> Text:
        max_len = max(len(x) for x in rumors)
        revealOrder = highlighter(repr(self.value.revealOrder))
        revealOrder.align('left', 3)
        return Text.assemble(
            Text.from_markup(f'[b]{self.name}[/b] '),
            ' ' * (max_len - len(self.name)),
            'revealOrder=',
            revealOrder,
            '  read=',
            color_bool(self.value.read, align_left=5),
            '  newlyRevealed=',
            color_bool(self.value.newlyRevealed, align_left=5),
        )


class GameSaveTree(Tree):
    # pylint: disable=too-many-instance-attributes
    BINDINGS = [
        ('o', 'open', 'Open'),
        ('S', 'save', 'Save'),
        ('space', 'edit_value', 'Edit'),
        ('space', 'toggle_value', 'Toggle'),
        Binding('space', 'toggle_node', 'Toggle', show=False),
        ('s', 'sort("reveal")', 'Sort (Reveal Order)'),
        ('s', 'sort("alpha")', 'Sort (Alphabetical)'),
        ('ctrl+r', 'set_log_state("reveal")', 'Toggle Reveal'),
        ('r', 'set_log_state("new_reveal")', 'Toggle Newly Revealed'),
        ('R', 'set_log_state("read")', 'Toggle Read'),
    ]

    class Action:
        OPEN = 'open'
        SAVE = 'save'
        EDIT_VALUE = 'edit_value'
        TOGGLE_VALUE = 'toggle_value'
        SORT = 'sort'
        SET_LOG_STATE = 'set_log_state'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__('GameSave', *args, **kwargs)

        class NamedNode:
            def __init__(self, name: str) -> None:
                self.name = name

            def __repr__(self) -> str:
                return f'NamedNode({self.name!r})'

        logger.debug('GameSaveTree.__init__()')
        self.root.expand()
        self.selected = None
        self.sorted_by = 'reveal'
        self.gamesave: Optional[GameSave] = None

        self.loopCount = self.root.add_leaf('', data=Entry('loopCount', 0, base_type=int))
        self.knownFrequencies = self.root.add('knownFrequencies')
        for i in range(7):
            self.knownFrequencies.add_leaf('', data=EntryBool(FrequencyEnum(i).name, False))

        self.knownSignals = self.root.add('knownSignals')
        for e in SignalEnum:
            self.knownSignals.add_leaf('', data=EntryBool(e.name, False))

        self.dictConditions = self.root.add('dictConditions')
        for condition in persistent_conditions:
            self.dictConditions.add_leaf('', data=EntryTristate(condition, Tristate(None)))

        self.shipLogFactSaves = self.root.add('shipLogFactSaves')
        self.shipLogFactSaves.data = NamedNode('shipLogFactSaves')

        self.newlyRevealedFactIDs = self.root.add_leaf(
            'newlyRevealedFactIDs',
            data=Entry(
                'newlyRevealedFactIDs',
                [],
                base_type=list,
            ),
        )
        self.lastDeathType = self.root.add_leaf(
            'lastDeathType',
            data=Entry(
                'lastDeathType',
                DeathTypeEnum.DEFAULT,
                value_transformer=lambda x: x.name,
                base_type=DeathTypeEnum,
                mode=Entry.DisplayMode.PLAIN,
            ),
        )
        self.burnedMarshmallowEaten = self.root.add_leaf(
            'burnedMarshmallowEaten', data=Entry('burnedMarshmallowEaten', 0, base_type=int)
        )
        self.fullTimeloops = self.root.add_leaf(
            'fullTimeloops',
            data=Entry(
                'fullTimeloops', 0, base_type=int, validator=Function(lambda x: int(x) >= 0, 'Must be non-negative')
            ),
        )
        self.warpedToTheEye = self.root.add_leaf('warpedToTheEye', data=EntryBool('warpedToTheEye', False))
        self.perfectMarshmallowsEaten = self.root.add_leaf(
            'perfectMarshmallowsEaten',
            data=Entry(
                'perfectMarshmallowsEaten',
                0,
                base_type=int,
                validator=Function(lambda x: int(x) >= 0, 'Must be non-negative'),
            ),
        )
        self.secondsRemainingOnWarp = self.root.add_leaf(
            'secondsRemainingOnWarp',
            data=Entry(
                'secondsRemainingOnWarp',
                0.0,
                base_type=float,
            ),
        )
        self.loopCountOnParadox = self.root.add_leaf(
            'loopCountOnParadox',
            data=Entry('loopCountOnParadox', 0, base_type=int),
        )
        self.shownPopups = self.root.add_leaf(
            'shownPopups',
            data=Entry(
                'shownPopups',
                StartupPopupsFlag(0),
                value_transformer=lambda x: '|'.join(y.name for y in x),
                base_type=StartupPopupsFlag,
                mode=Entry.DisplayMode.PLAIN,
            ),
        )
        self.version = self.root.add_leaf(
            'version',
            data=Entry('version', '', base_type=str),
        )
        self.ps5Activity_canResumeExpedition = self.root.add_leaf(
            'ps5Activity_canResumeExpedition',
            data=EntryBool('ps5Activity_canResumeExpedition', False),
        )
        self.ps5Activity_availableShipLogCards = self.root.add_leaf(
            'ps5Activity_availableShipLogCards',
            data=Entry(
                'ps5Activity_availableShipLogCards',
                [],
                base_type=list,
                enabled=False,
            ),
        )
        self.didRunInitGammaSetting = self.root.add_leaf(
            'didRunInitGammaSetting',
            data=EntryBool('didRunInitGammaSetting', False),
        )

        self.set_gamesave(GameSave())

        self.update_labels()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:  # noqa: PLR0912
        # logger.debug('GameSaveTree.check_action(%s, %s)', action, parameters)
        # logger.debug(' - %r %r', self.selected, self.selected.data.name if self.selected.data else None)
        ret = True
        if action not in ('edit_value', 'toggle_value', 'sort', 'set_log_state'):
            return True

        if not (self.selected and self.selected.data is not None):
            return False

        if action == self.Action.SORT:
            if self.shipLogFactSaves in (self.selected, self.selected.parent):
                ret = parameters[0] == {'reveal': 'alpha', 'alpha': 'reveal'}[self.sorted_by]

            else:
                ret = False
        elif action == self.Action.OPEN:
            ret = self.gamesave is None
        elif action == self.Action.SAVE:
            ret = self.gamesave is not None
        elif isinstance(self.selected.data, Entry):
            if action == self.Action.EDIT_VALUE:
                ret = (
                    type(self.selected.data.value)
                    in (str, int, float, ShipLogFactSave, DeathTypeEnum, StartupPopupsFlag)
                    and self.has_focus
                )
            elif action == self.Action.TOGGLE_VALUE:
                ret = isinstance(self.selected.data.value, (Tristate, bool)) and self.has_focus
            elif action == self.Action.SET_LOG_STATE:
                ret = self.selected.parent == self.shipLogFactSaves
            else:
                ret = False
        else:
            ret = False

        return ret

    async def on_click(self, event: Click) -> None:
        # logger.info('on_click(%r)', event)
        if event.widget.id == 'tree' and event.chain % 2 == 0:  # noqa
            await self.action_edit_value()

    def action_open(self) -> None:
        self.run_worker(self._open())

    async def _open(self) -> None:
        file = self.app.config.get('file')
        if not file:
            file = await self.app.push_screen_wait(FileOpen())

        logger.info('Opening to %r', file)
        with Path(file).open() as file:
            self.set_gamesave(GameSave.from_json(file))

        self.root.expand()
        self.refresh_bindings()

    def action_save(self) -> None:
        # logger.debug('action_save()')
        self.run_worker(self._save())

    async def _save(self) -> None:
        # logger.debug('_save()')
        file = self.app.config.get('outfile')
        if not file:
            file = await self.app.push_screen_wait(FileSave())
        logger.info('Saving to %r', file)

        self.update_gamesave()
        self.gamesave.save(file)

    async def action_toggle_value(self) -> None:
        if not self.selected or not self.selected.data:
            return

        if isinstance(self.selected.data.value, Tristate):
            self.submit_edit({True: False, False: None, None: True}[self.selected.data.value.value])
        elif isinstance(self.selected.data.value, bool):
            # logger.debug('action_toggle(%s)', self.selected.data.value)
            self.submit_edit(not self.selected.data.value)
        else:
            raise ValueError('Called action_toggle on a non-toggleable Entry')

    async def action_edit_value(self) -> None:
        # logger.info('action_edit_value | %r', self.selected)
        if not (self.selected and isinstance(self.selected.data, Entry) and self.selected.data.enabled):
            return

        data_type = self.selected.data.type
        value = self.selected.data.value

        if data_type in (Tristate, bool):
            await self.action_toggle_value()
            return

        if data_type in (DeathTypeEnum,):
            await self.app.optionlist.set_options([x.name for x in DeathTypeEnum], self.app.optionlist.ModeEnum.SINGLE)
            self.app.optionlist.options[self.lastDeathType.data.value].set(True)

            self.app.optionlist.index = int(self.lastDeathType.data.value)
            self.app.optionlist.show()
            return

        if data_type in (StartupPopupsFlag,):
            await self.app.optionlist.set_options(
                [x.name for x in StartupPopupsFlag], self.app.optionlist.ModeEnum.MULTI
            )
            for n, flag in enumerate(list(StartupPopupsFlag)):
                self.app.optionlist.options[n].set(value & flag > 0)

            self.app.optionlist.index = 0
            self.app.optionlist.show()
            return

        widget = self.app.query_one('#editbox', Input)

        widget.validators = []
        if self.selected.data.validator:
            widget.validators.append(ValidationWrapper(self.selected.data.validator))

        if isinstance(self.selected.data.value, ShipLogFactSave):
            value = self.selected.data.value.revealOrder
            data_type = int

        # logger.debug(
        #     'Selected Entry: %r. Editing with value %r and type %r',
        #     self.selected.data,
        #     value,
        #     data_type,
        # )

        widget.disabled = False
        widget.styles.display = 'block'
        widget.value = str(value)

        if data_type is float:
            widget.type = 'numeric'
            widget.restrict = r'^-?[0-9]*(?:\.[0-9]*)?$'
        elif data_type is int:
            widget.type = 'integer'
            widget.restrict = r'^-?[0-9]*$'
        else:
            widget.type = 'text'
            widget.restrict = None

        widget.focus()

    async def action_set_log_state(self, parameter: str) -> None:
        # logger.debug('action_set_log_state(%r)', parameter)
        if parameter == 'read':
            self.selected.data.value.read = not self.selected.data.value.read
        elif parameter == 'reveal':
            revealOrder = self.selected.data.value.revealOrder
            if revealOrder > -1:
                self.submit_edit(-1)
                self.selected.data.value.newlyRevealed = False
                self.newlyRevealedFactIDs.data.value = [
                    x for x in self.newlyRevealedFactIDs.data.value if x != self.selected.data.value.id
                ]
            else:
                self.submit_edit(max(x.data.value.revealOrder + 1 for x in self.shipLogFactSaves.children))
                self.selected.data.value.newlyRevealed = True
                self.newlyRevealedFactIDs.data.value.append(self.selected.data.value.id)
        elif parameter == 'new_reveal':
            self.selected.data.value.newlyRevealed = not self.selected.data.value.newlyRevealed
            if self.selected.data.value.newlyRevealed:
                self.newlyRevealedFactIDs.data.value.append(self.selected.data.value.id)
            else:
                self.newlyRevealedFactIDs.data.value = [
                    x for x in self.newlyRevealedFactIDs.data.value if x != self.selected.data.value.id
                ]
        else:
            raise ValueError('action_set_log_state called without "read" nor "reveal"')

        self.update_labels()

    def action_sort(self, sort_by: str) -> None:
        # logger.info('sorting, sort_by:%r, sorted_by: %r', sort_by, self.sorted_by)

        if sort_by == 'reveal':

            def key(x: object) -> object:
                return x.data.value.revealOrder

        elif sort_by == 'alpha':

            def key(x: object) -> object:
                return x.data.value.id

        else:
            raise ValueError(f'Invalid sort method: {sort_by!r}')

        self.sorted_by = sort_by

        children = list(self.shipLogFactSaves.children)
        children.sort(key=key, reverse=True)
        self.shipLogFactSaves._children = []  # pylint: disable=protected-access
        for node in children:
            self.shipLogFactSaves._children.insert(0, node)  # pylint: disable=protected-access
        self._invalidate()

        # logger.info(
        #     ' - refresh_bindings',
        # )
        self.app.refresh_bindings()

        if self.selected:
            self.scroll_to_node(self.selected)

            line = self.selected._line  # pylint: disable=protected-access
            visible = self.size.height
            self.scroll_y = max(line - visible // 2, 0)

    def update_labels(self) -> None:
        def helper(node: TreeNode) -> None:
            for child in node.children:
                if child.data and isinstance(child.data, Entry):
                    child.set_label(child.data.get_label())
                if len(child.children):
                    helper(child)

        helper(self.root)

    def action_submit(self) -> None:
        # logger.debug('action_edit(%s)', self.app.optionlist.index)
        if self.app.editbox.has_focus:
            if not self.app.editbox.is_valid:
                return
            self.submit_edit(self.app.editbox.value)
        elif self.app.optionlist.has_focus:
            if isinstance(self.selected.data.value, DeathTypeEnum):
                self.submit_edit(DeathTypeEnum(self.app.optionlist.index))
            elif isinstance(self.selected.data.value, StartupPopupsFlag):
                val = StartupPopupsFlag.NONE
                for n, option in enumerate(self.app.optionlist.options):
                    val |= int(option.value) << n
                self.submit_edit(val)
        self.app.optionlist.hide()
        self.app.hide_editbox()
        self.focus()

    def submit_edit(self, new_value: object = None) -> None:
        # logger.debug('edit(%s)', new_value)
        if self.selected is None or self.selected.data is None or not isinstance(self.selected.data, Entry):
            return

        data_type = self.selected.data.type
        if data_type is int:
            self.selected.data.value = int(new_value)
        elif data_type is float:
            self.selected.data.value = float(new_value)
        elif data_type is str:
            self.selected.data.value = str(new_value)
        elif data_type in (bool, Tristate, DeathTypeEnum, StartupPopupsFlag):
            self.selected.data.value = data_type(new_value)
        elif isinstance(self.selected.data.value, ShipLogFactSave):
            old_value = self.selected.data.value.revealOrder
            new_value = int(new_value)
            n = c = 0
            for fact in sorted(self.shipLogFactSaves.children, key=lambda x: x.data.value.revealOrder):
                if fact.data.value.revealOrder == -1:
                    continue

                if fact.data.value.revealOrder == old_value:
                    continue
                if c == new_value:
                    c += 1
                fact.data.value.revealOrder = c
                c += 1
                n += 1

            new_value = min(new_value, max(x.data.value.revealOrder + 1 for x in self.shipLogFactSaves.children))
            self.selected.data.value.revealOrder = new_value
            self.action_sort(self.sorted_by)

        else:
            raise ValueError('Trying to set value of a Entry with unsure base type')

        self.update_labels()

        self.app.hide_editbox()

    def on_tree_node_highlighted(self, event: Tree.NodeSelected) -> None:
        self.selected = event.node
        self.app.refresh_bindings()

    def set_gamesave(self, gamesave: GameSave) -> None:
        # logger.debug('set_gamesave()')
        self.gamesave = gamesave

        if not isinstance(self.loopCount.data, Entry):
            raise ValueError('loopCount.data must be an Entry')

        self.loopCount.data.value = gamesave.loopCount

        for frequency, node in product(gamesave.knownFrequencies, self.knownFrequencies.children):
            if not isinstance(node.data, Entry):
                raise ValueError('frequency <node>.data must be an Entry')
            if node.data.name == frequency.name:
                node.data.value = gamesave.knownFrequencies[frequency]

        for signal, node in product(gamesave.knownSignals, self.knownSignals.children):
            if not isinstance(node.data, Entry):
                raise ValueError('knownSignal <node>.data must be an Entry')
            if node.data.name == signal.name:
                node.data.value = gamesave.knownSignals[signal]

        for condition, node in product(gamesave.dictConditions, self.dictConditions.children):
            if not isinstance(node.data, Entry):
                raise ValueError('dictCondition <node>.data must be an Entry')
            if node.data.name == condition:
                node.data.value = gamesave.dictConditions[condition]

        self.shipLogFactSaves.remove_children()
        for k, v in sorted(gamesave.shipLogFactSaves.items(), key=lambda x: x[1].revealOrder):
            node = self.shipLogFactSaves.add_leaf(k)
            node.data = EntrySaveLogFact(
                k,
                v,
                validator=Function(
                    lambda x: -1
                    <= int(x)
                    <= max(
                        x.data.value.revealOrder + 1 if x.data is not None else 0
                        for x in self.shipLogFactSaves.children
                    ),
                    'Out of range',
                ),
            )
        #  for n, node in enumerate(self.shipLogFactSaves.children):
        #  node.data.value = gamesave.shipLogFactSaves[node.data.name]

        # self.newlyRevealedFactIDs: list[str] = []
        self.newlyRevealedFactIDs.data.value = gamesave.newlyRevealedFactIDs
        self.lastDeathType.data.value = gamesave.lastDeathType
        self.burnedMarshmallowEaten.data.value = gamesave.burnedMarshmallowEaten
        self.fullTimeloops.data.value = gamesave.fullTimeloops
        self.warpedToTheEye.data.value = gamesave.warpedToTheEye
        self.perfectMarshmallowsEaten.data.value = gamesave.perfectMarshmallowsEaten
        self.secondsRemainingOnWarp.data.value = gamesave.secondsRemainingOnWarp
        self.loopCountOnParadox.data.value = gamesave.loopCountOnParadox
        self.shownPopups.data.value = gamesave.shownPopups
        self.version.data.value = gamesave.version
        self.ps5Activity_canResumeExpedition.data.value = gamesave.ps5Activity_canResumeExpedition
        self.ps5Activity_availableShipLogCards.data.value = gamesave.ps5Activity_availableShipLogCards
        self.didRunInitGammaSetting.data.value = gamesave.didRunInitGammaSetting

        self.update_labels()

    def update_gamesave(self) -> bool:
        if not self.gamesave:
            return False

        self.gamesave.loopCount = self.loopCount.data.value

        for frequency, node in product(self.gamesave.knownFrequencies, self.knownFrequencies.children):
            if node.data.name == frequency.name:
                self.gamesave.knownFrequencies[frequency] = node.data.value

        for signal, node in product(self.gamesave.knownSignals, self.knownSignals.children):
            if node.data.name == signal.name:
                self.gamesave.knownSignals[signal] = node.data.value

        for condition, node in product(self.gamesave.dictConditions, self.dictConditions.children):
            if node.data.name == condition:
                self.gamesave.dictConditions[condition] = node.data.value

        self.gamesave.shipLogFactSaves = {}
        for node in self.shipLogFactSaves.children:
            entry: Entry = node.data
            self.gamesave.shipLogFactSaves[entry.value.id] = entry.value

        # self.newlyRevealedFactIDs: list[str] = []

        self.gamesave.newlyRevealedFactIDs = self.newlyRevealedFactIDs.data.value
        # for node in self.shipLogFactSaves.children:
        #     entry: Entry = node.data
        #     self.gamesave.newlyRevealedFactIDs.append(entry.value)

        self.gamesave.lastDeathType = self.lastDeathType.data.value
        self.gamesave.burnedMarshmallowEaten = self.burnedMarshmallowEaten.data.value
        self.gamesave.fullTimeloops = self.fullTimeloops.data.value
        self.gamesave.warpedToTheEye = self.warpedToTheEye.data.value
        self.gamesave.perfectMarshmallowsEaten = self.perfectMarshmallowsEaten.data.value
        self.gamesave.secondsRemainingOnWarp = self.secondsRemainingOnWarp.data.value
        self.gamesave.loopCountOnParadox = self.loopCountOnParadox.data.value
        self.gamesave.shownPopups = self.shownPopups.data.value
        self.gamesave.version = self.version.data.value
        self.gamesave.ps5Activity_canResumeExpedition = self.ps5Activity_canResumeExpedition.data.value
        # self.gaesave.ps5Activity_availableShipLogCards = self.ps5Activity_availableShipLogCards.data.value
        self.gamesave.didRunInitGammaSetting = self.didRunInitGammaSetting.data.value
