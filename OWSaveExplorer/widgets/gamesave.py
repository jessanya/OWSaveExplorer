#!/usr/bin/env python

import logging
from itertools import product
from typing import Callable, Optional

from rich.text import Text
from textual.events import Click
from textual.widgets import Input, Tree
from textual.widgets.tree import TreeNode

from OWSaveExplorer.enums import (
    DeathTypeEnum,
    FrequencyEnum,
    SignalEnum,
    StartupPopupsFlag,
)
from OWSaveExplorer.gamesave import GameSave, ShipLogFactSave
from OWSaveExplorer.strings import persistent_conditions, rumors
from OWSaveExplorer.util import Tristate, color_bool, highlighter

logger = logging.getLogger('gamesave')


class Entry:
    def __init__(
        self,
        name: str,
        value: Optional[object] = None,
        value_transformer: Optional[Callable] = None,
        base_type: Optional[type] = None,
        repr_: bool = True,
    ) -> None:
        self.name = name
        self.value = value
        self.value_transformer = value_transformer if value_transformer else lambda x: x
        self.repr = repr_
        self.type = base_type

    def set(self, value: object) -> None:
        self.value = value

    def get(self) -> object:
        return self.value

    def get_label(self) -> Text:
        #  color = self.get_color()
        color_prefix = color_suffix = ''
        # if color:
        #    color_prefix = f'[{color}]'
        #    color_suffix = f'[/]'

        value = self.value_transformer(self.value)

        if isinstance(value, bool):
            value_text = color_bool(value)
        elif value is None:
            value_text = Text.from_markup(f'[yellow]{value}[/]')
        else:
            value_text = highlighter(repr(value) if self.repr else value)

        logger.debug('get_label(%r) -> %s | %r', self, self.name, value)
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

    def validate(self, value: object) -> bool:
        return True


class EntryTristate(Entry):
    def __init__(self, *args) -> None:
        self.value: Tristate
        super().__init__(*args, value_transformer=lambda x: x.value, base_type=Tristate)

    def get_color(self) -> str:
        return {False: 'red', True: 'green', None: 'yellow'}[self.value.value]


class EntryBool(Entry):
    def __init__(self, *args) -> None:
        self.value = False
        super().__init__(*args, base_type=bool)

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

    def validate(self, value: int) -> bool:
        return value >= -1


class GameSaveWidget(Tree):
    # pylint: disable=too-many-instance-attributes
    BINDINGS = [
        ('e', 'edit', 'Edit'),
        ('t', 'toggle', 'Toggle'),
        ('s', 'sort("reveal")', 'Sort (Reveal Order)'),
        ('s', 'sort("alpha")', 'Sort (Alphabetical)'),
        ('r', 'set_log_state("reveal")', 'Toggle Reveal'),
        ('R', 'set_log_state("read")', 'Toggle Read'),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__('GameSave', *args, **kwargs)
        self.root.expand()
        self.selected = None
        self.sorted_by = 'alpha'
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
        self.shipLogFactSaves.data = {'name': 'shipLogFactSaves'}

        self.update_labels()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        #  logger.debug(f'GameSaveWidget.check_action()')
        ret = True
        if action not in ('edit', 'toggle', 'sort', 'set_log_state'):
            return True

        if not (self.selected and isinstance(self.selected.data, Entry)):
            return False

        if action == 'edit':
            ret = type(self.selected.data.value) in (str, int, float, ShipLogFactSave)
        elif action == 'toggle':
            ret = isinstance(self.selected.data.value, (Tristate, bool))
        elif action == 'sort':
            if (
                self.selected.parent
                and isinstance(self.selected.parent.data, dict)
                and self.selected.parent.data.get('name', None) == 'shipLogFactSaves'
            ):
                ret = parameters[0] == {'reveal': 'alpha', 'alpha': 'reveal'}[self.sorted_by]

            else:
                ret = False
        elif action == 'set_log_state':
            ret = (
                self.selected.parent
                and isinstance(self.selected.parent.data, dict)
                and self.selected.parent.data.get('name', None) == 'shipLogFactSaves'
            )

        return ret

    async def on_click(self, event: Click) -> None:
        if event.widget.id == 'tree' and event.chain == 2:  # noqa
            self.action_edit()

    async def action_toggle(self) -> None:
        if not self.selected or not self.selected.data:
            return

        self.edit()

    def action_edit(self) -> None:
        if not (self.selected and isinstance(self.selected.data, Entry)):
            return

        data_type = self.selected.data.type
        value = self.selected.data.value

        if data_type in (Tristate, bool):
            return

        widget = self.app.query_one('#editbox', Input)
        widget.validators = []

        if isinstance(self.selected.data.value, ShipLogFactSave):
            value = self.selected.data.value.revealOrder
            data_type = int
            #  class MyValidator(Validator):
            widget.validators = []

        logger.debug(
            'Selected Entry: %r. Editing with value %r and type %r',
            self.selected.data,
            value,
            data_type,
        )

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
        logger.debug('action_set_log_state(%r)', parameter)
        if parameter == 'read':
            self.selected.data.value.read = not self.selected.data.value.read
        elif parameter == 'reveal':
            revealOrder = self.selected.data.value.reveal
            if revealOrder > -1:
                pass
        else:
            raise ValueError('action_set_log_state called without "read" nor "reveal"')

        self.update_labels()
        # = not self.selected.data.value.reveal

    async def action_sort(self, sort_by: str) -> None:
        if not (
            self.selected.parent
            and isinstance(self.selected.parent.data, dict)
            and self.selected.parent.data.get('name', None) == 'shipLogFactSaves'
        ):
            return

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

        self.app.refresh_bindings()

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

    def edit(self, new_value: object = None) -> None:
        logger.debug('edit(%s)', new_value)
        if self.selected is None or self.selected.data is None or not isinstance(self.selected.data, Entry):
            return

        if isinstance(self.selected.data.value, Tristate):
            self.selected.data.value.value = {True: False, False: None, None: True}[self.selected.data.value.value]
        elif isinstance(self.selected.data.value, bool):
            self.selected.data.value = not self.selected.data.value

        if new_value:
            data_type = self.selected.data.type
            if data_type is int:
                self.selected.data.value = int(new_value)
            elif data_type is float:
                self.selected.data.value = float(new_value)
            elif data_type is str:
                self.selected.data.value = str(new_value)
            elif isinstance(self.selected.data.value, ShipLogFactSave):
                self.selected.data.value.revealOrder = int(new_value)
            else:
                raise ValueError('Trying to set value of a Entry with unsure base type')

        self.update_labels()

        self.app.hide_editbox()

        logger.debug(self.selected)

    def on_tree_node_highlighted(self, event: Tree.NodeSelected) -> None:
        self.selected = event.node
        #  self.
        self.app.refresh_bindings()
        logger.debug(self.selected)

    def set_gamesave(self, gamesave: GameSave) -> None:
        logger.debug('set_gamesave()')
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
        for k, v in sorted(gamesave.shipLogFactSaves.items(), key=lambda x: x[1].id):
            node = self.shipLogFactSaves.add_leaf(k)
            node.data = EntrySaveLogFact(k, v)
        #  for n, node in enumerate(self.shipLogFactSaves.children):
        #  node.data.value = gamesave.shipLogFactSaves[node.data.name]

        # self.newlyRevealedFactIDs: list[str] = []
        self.newlyRevealedFactIDs = self.root.add_leaf(
            'newlyRevealedFactIDs',
            data=Entry(
                'newlyRevealedFactIDs',
                gamesave.newlyRevealedFactIDs,
                base_type=list,
            ),
        )

        logger.debug('lastDeathType(%s)', gamesave.lastDeathType)
        self.lastDeathType = self.root.add_leaf(
            'lastDeathType',
            data=Entry(
                'lastDeathType',
                gamesave.lastDeathType,
                value_transformer=lambda x: x.name,
                base_type=DeathTypeEnum,
            ),
        )
        self.burnedMarshmallowEaten = self.root.add_leaf(
            'burnedMarshmallowEaten',
            data=Entry('burnedMarshmallowEaten', gamesave.burnedMarshmallowEaten, base_type=int),
        )
        self.fullTimeloops = self.root.add_leaf(
            'fullTimeloops',
            data=Entry('fullTimeloops', gamesave.fullTimeloops, base_type=int),
        )
        self.warpedToTheEye = self.root.add_leaf(
            'warpedToTheEye', data=EntryBool('warpedToTheEye', gamesave.warpedToTheEye)
        )
        self.perfectMarshmallowsEaten = self.root.add_leaf(
            'perfectMarshmallowsEaten',
            data=Entry(
                'perfectMarshmallowsEaten',
                gamesave.perfectMarshmallowsEaten,
                base_type=int,
            ),
        )

        self.secondsRemainingOnWarp = self.root.add_leaf(
            'secondsRemainingOnWarp',
            data=Entry(
                'secondsRemainingOnWarp',
                gamesave.secondsRemainingOnWarp,
                base_type=float,
            ),
        )
        self.loopCountOnParadox = self.root.add_leaf(
            'loopCountOnParadox',
            data=Entry('loopCountOnParadox', gamesave.loopCountOnParadox, base_type=int),
        )
        self.shownPopups = self.root.add_leaf(
            'shownPopups',
            data=Entry(
                'shownPopups',
                gamesave.shownPopups,
                value_transformer=lambda x: '|'.join(y.name for y in x),
                base_type=StartupPopupsFlag,
                repr_=False,
            ),
        )
        self.version = self.root.add_leaf(
            'version',
            data=Entry('version', gamesave.version, base_type=str),
        )
        self.ps5Activity_canResumeExpedition = self.root.add_leaf(
            'ps5Activity_canResumeExpedition',
            data=EntryBool(
                'ps5Activity_canResumeExpedition',
                gamesave.ps5Activity_canResumeExpedition,
            ),
        )
        self.ps5Activity_availableShipLogCards = self.root.add_leaf(
            'ps5Activity_availableShipLogCards',
            data=Entry(
                'ps5Activity_availableShipLogCards',
                gamesave.ps5Activity_availableShipLogCards,
                base_type=list,
            ),
        )

        self.didRunInitGammaSetting = self.root.add_leaf(
            'didRunInitGammaSetting',
            data=EntryBool('didRunInitGammaSetting', gamesave.didRunInitGammaSetting),
        )

        self.update_labels()
