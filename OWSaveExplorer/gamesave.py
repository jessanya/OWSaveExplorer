#!/usr/bin/env python

import logging
from collections.abc import Iterator
from io import TextIOBase
from json import dumps, loads
from pathlib import Path
from pprint import PrettyPrinter
from typing import Any, Optional, Union

from OWSaveExplorer.enums import (
    DeathTypeEnum,
    FrequencyEnum,
    SignalEnum,
    StartupPopupsFlag,
)
from OWSaveExplorer.strings import persistent_conditions, rumors
from OWSaveExplorer.util import Tristate

logger = logging.getLogger('gamesave')

class ShipLogFactSave:
    def __init__(
        self,
        id_: str,
        revealOrder: int = -1,
        read: bool = False,
        newlyRevealed: bool = False,
    ) -> None:
        self.id = id_
        self.revealOrder = revealOrder
        self.read = read
        self.newlyRevealed = newlyRevealed

    @classmethod
    def from_dict(cls, data: dict) -> 'ShipLogFactSave':
        return cls(data['id'], data['revealOrder'], data['read'], data['newlyRevealed'])

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        yield from {
            'id': self.id,
            'revealOrder': self.revealOrder,
            'read': self.read,
            'newlyRevealed': self.newlyRevealed,
        }.items()

    def __repr__(self) -> str:
        return (
            f'ShipLogFactSave(id={self.id!r}, revealOrder={self.revealOrder}, read={self.read}, '
            f'newlyRevealed={self.newlyRevealed})'
        )


# class ShipLogFactSavesNode:
#     def __init__(self, node):
#         self.node = node

#     def _next

#     def reveal(name):


class GameSave:
    def __init__(self) -> None:
        self.loopCount: int = 1

        self.knownFrequencies: dict[FrequencyEnum, bool] = {}
        for i in range(7):
            self.knownFrequencies[FrequencyEnum(i)] = False
        self.knownFrequencies[FrequencyEnum._] = True

        self.knownSignals: dict[SignalEnum, bool] = {}
        for signal in list(SignalEnum):
            self.knownSignals[signal] = False

        self.dictConditions: dict[str, Tristate] = {}

        self.shipLogFactSaves: dict[str, ShipLogFactSave] = {}
        for fact in rumors:
            self.shipLogFactSaves[fact] = ShipLogFactSave(id_=fact)

        self.newlyRevealedFactIDs: list[str] = []
        self.lastDeathType: DeathTypeEnum = DeathTypeEnum.DEFAULT
        self.burnedMarshmallowEaten: int = 0
        self.fullTimeloops: int = 0  # uint
        self.perfectMarshmallowsEaten: int = 0  # uint
        self.warpedToTheEye: bool = False
        self.secondsRemainingOnWarp: float = 0.0
        self.loopCountOnParadox: int = 0
        self.shownPopups: StartupPopupsFlag = StartupPopupsFlag.NONE
        self.version: str = 'NONE'
        self.ps5Activity_canResumeExpedition: bool = False
        self.ps5Activity_availableShipLogCards: list[str] = []
        self.didRunInitGammaSetting: bool = False

    @classmethod
    def from_json(cls, json: Union[str, TextIOBase]) -> 'GameSave':
        save = cls()
        if isinstance(json, TextIOBase):
            json = json.read()

        data = loads(json)
        save.loopCount = data['loopCount']

        for k, v in enumerate(data['knownFrequencies']):
            save.knownFrequencies[FrequencyEnum(int(k))] = v

        for k, v in data['knownSignals'].items():
            save.knownSignals[SignalEnum(int(k))] = v

        for condition in persistent_conditions:
            save.dictConditions[condition] = Tristate(data['dictConditions'].get(condition))

        for k, v in data['shipLogFactSaves'].items():
            save.shipLogFactSaves[k] = ShipLogFactSave.from_dict(v)

        save.newlyRevealedFactIDs = data['newlyRevealedFactIDs']
        save.lastDeathType = DeathTypeEnum(data['lastDeathType'])
        save.burnedMarshmallowEaten = data['burnedMarshmallowEaten']
        save.fullTimeloops = data['fullTimeloops']
        save.perfectMarshmallowsEaten = data['perfectMarshmallowsEaten']
        save.warpedToTheEye = data['warpedToTheEye']
        save.secondsRemainingOnWarp = data['secondsRemainingOnWarp']
        save.loopCountOnParadox = data['loopCountOnParadox']
        save.shownPopups = StartupPopupsFlag(data['shownPopups'])
        save.version = data['version']
        save.ps5Activity_canResumeExpedition = data['ps5Activity_canResumeExpedition']
        save.ps5Activity_availableShipLogCards = data['ps5Activity_availableShipLogCards']
        save.didRunInitGammaSetting = data['didRunInitGammaSetting']

        return save

    def to_json(self) -> str:
        data = {}
        data['loopCount'] = self.loopCount

        data['knownFrequencies']: list[bool] = [self.knownFrequencies[FrequencyEnum(n)] for n in range(7)]

        data['knownSignals']: dict[SignalEnum, bool] = {}
        for signal, v in self.knownSignals.items():
            data['knownSignals'][str(int(signal))] = v

        data['dictConditions'] = {}
        for condition, v in self.dictConditions.items():
            if v is not None and v.value is not None:
                data['dictConditions'][condition] = v.value

        data['shipLogFactSaves'] = {}
        for k, v in self.shipLogFactSaves.items():
            data['shipLogFactSaves'][k] = dict(v)

        data['newlyRevealedFactIDs'] = self.newlyRevealedFactIDs
        data['lastDeathType'] = int(self.lastDeathType)

        data['burnedMarshmallowEaten'] = self.burnedMarshmallowEaten
        data['fullTimeloops'] = self.fullTimeloops
        data['perfectMarshmallowsEaten'] = self.perfectMarshmallowsEaten
        data['warpedToTheEye'] = self.warpedToTheEye
        data['secondsRemainingOnWarp'] = self.secondsRemainingOnWarp
        data['loopCountOnParadox'] = self.loopCountOnParadox
        data['shownPopups'] = int(self.shownPopups)
        data['version'] = self.version
        data['ps5Activity_canResumeExpedition'] = self.ps5Activity_canResumeExpedition
        data['ps5Activity_availableShipLogCards'] = self.ps5Activity_availableShipLogCards
        data['didRunInitGammaSetting'] = self.didRunInitGammaSetting

        self.from_json(dumps(data))

        return dumps(data)

    def save(self, file: str | Path | TextIOBase) -> None:
        if isinstance(file, str):
            file = Path(file).open('w')  # noqa: SIM115
        elif isinstance(file, Path):
            file = file.open('w')
        elif not isinstance(file, str):
            raise ValueError('"file" argument must be a str, Path, or TextIOBase')

        json = self.to_json()
        file.write(json)

    def __repr__(self) -> str:
        out = 'GameSave('
        out += f'loopCount={self.loopCount}, knownFrequencies={{...}}, '
        out += 'knownSignals={{...}}, dictConditions={{...}}, shipLogFactSaves={{...}}, '
        out += f'self.newlyRevealedFactIDs = [...], lastDeathType={self.lastDeathType}, '
        out += f'burnedMarshmallowEaten={self.burnedMarshmallowEaten}, fullTimeloops={self.fullTimeloops}, '
        out += f'perfectMarshmallowsEaten={self.perfectMarshmallowsEaten}, warpedToTheEye={self.warpedToTheEye}, '
        out += f'secondsRemainingOnWarp={self.secondsRemainingOnWarp}, loopCountOnParadox={self.loopCountOnParadox}, '
        out += f'shownPopups={self.shownPopups}, version={self.version}'
        out += ')'
        return out


if isinstance(PrettyPrinter._dispatch, dict):

    def pprint_GameSave(  # noqa: PLR0913
        printer: PrettyPrinter,
        object: object,
        stream: Optional[TextIOBase],
        indent: int,
        allowance: int,
        context: dict,
        level: int,
    ) -> None:
        stream.write('GameSave(\n')
        ipl = printer._indent_per_level + 1
        indent += printer._indent_per_level  # len(GameSave.__name__)
        stream.write(' ' * ipl + f'loopCount: {object.loopCount}\n')

        stream.write(' ' * ipl + 'knownFrequencies:\n')
        max_len = max(len(x.name) for x in FrequencyEnum)
        for n, v in enumerate(object.knownFrequencies):
            stream.write(' ' * (ipl * 2))
            stream.write(f'{FrequencyEnum(n).name.ljust(max_len)}: {v}\n')

        stream.write(' ' * ipl + 'knownSignals:\n')
        max_len = max(len(x.name) for x in object.knownSignals)
        for k, v in object.knownSignals.items():
            stream.write(' ' * (ipl * 2))
            stream.write(f'{k.name.ljust(max_len)}: {v}\n')

        stream.write(' ' * ipl + 'dictConditions:\n')
        max_len = max(len(x) for x in object.dictConditions)
        for k, v in object.dictConditions.items():
            stream.write(' ' * (ipl * 2))
            stream.write(f'{k.ljust(max_len)}: {v}\n')

        stream.write(' ' * ipl + 'shipLogFactSaves:\n')
        max_len = max(len(x) for x in object.dictConditions)
        items = list(object.shipLogFactSaves.items())
        items.sort(key=lambda x: (x[1].revealOrder, x[0]))
        for k, v in items:
            stream.write(' ' * (ipl * 2))
            read = ' read' if v.read else ''
            newlyRevealed = ' newlyRevealed' if v.newlyRevealed else ''
            stream.write(f'{k.ljust(max_len)}: revealOrder={v.revealOrder:<3}{read}{newlyRevealed}\n')

        stream.write(' ' * ipl + f'lastDeathType: {object.lastDeathType}\n')
        stream.write(' ' * ipl + f'burnedMarshmallowEaten: {object.burnedMarshmallowEaten}\n')
        stream.write(' ' * ipl + f'fullTimeloops: {object.fullTimeloops}\n')
        stream.write(' ' * ipl + f'perfectMarshmallowsEaten: {object.perfectMarshmallowsEaten}\n')
        stream.write(' ' * ipl + f'warpedToTheEye: {object.warpedToTheEye}\n')
        stream.write(' ' * ipl + f'secondsRemainingOnWarp: {object.secondsRemainingOnWarp}\n')
        stream.write(' ' * ipl + f'loopCountOnParadox: {object.loopCountOnParadox}\n')
        stream.write(' ' * ipl + f'shownPopups: {object.shownPopups}\n')
        stream.write(' ' * ipl + f'version: {object.version}\n')

        stream.write(')')

    PrettyPrinter._dispatch[GameSave.__repr__] = pprint_GameSave
