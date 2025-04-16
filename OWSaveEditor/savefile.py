#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional, Union
from io import TextIOBase

import pprint
from enum import Enum, auto, Flag
import json
import logging
from rich.text import Text

from .strings import persistent_conditions, frequencies
from .util import highlighter, Tristate

logger = logging.getLogger('savefile')

class Entry:
  def __init__(self, name, value=None):
      self.name = name
      self.value = value

  def set(self, value):
      self.value = value

  def get(self):
      return self.value

  def get_label(self):
      color = self.get_color()
      color_prefix = color_suffix = ''
      if color:
          color_prefix = f'[{color}]'
          color_suffix = f'[/]'
      return Text.assemble(Text.from_markup(f'{color_prefix}[b]{self.name}[/b]{color_suffix}='), highlighter(repr(self.value)))

  def __repr__(self):
      return f'Entry(name={self.name!r}, value={self.value!r})'

  def get_color(self):
      return None

  def get_type(self):
      return type(self.value)

class Tristate(Entry):
  def toggle(self):
      if self.value:
          self.value = False
      elif self.value == False:
          self.value = None
      else:
          self.value = True

class Bistate(Entry):
  def toggle(self):
      self.value = not self.value

conditions = []
class Condition(Tristate):
  class ConditionType(Enum):
      PERSISTENT=0
      TEMPORARY=1
  def __init__(self, name, value=None, type_: ConditionType = ConditionType.PERSISTENT):
      super().__init__(name, value)
      self.type = type_

  def __repr__(self):
      return f'Condition(name={self.name!r}, value={self.value!r})'#, type={self.type})'

  @classmethod
  def load_conditions(cls):
      global conditions
      for condition in persistent_conditions:
          conditions.append(Condition(condition))

  def get_color(self):
      return {True: None, False: 'red', None: 'yellow'}[self.value]




Condition.load_conditions()

class SaveFile:
  def __init__(self, fn):
      self.data = json.load(open(fn))

      known = self.data['knownFrequencies']
      for n, frequency in enumerate(known):
          known[n] = Entry(frequencies.get(str(n), str(n)) + f'({n})', known[n])
          #  text = f'{frequencies.get(name, name)}({name})'

      #  known = self.data['knownSignals']
      #  for k, v in known.items():
          #  known[k] = Bistate(k, v)
          #  text = f'{frequencies.get(name, name)}({name})'

      conditions_in_file = []
      dictConditions = self.data['dictConditions']
      for k, v in dictConditions.items():
          dictConditions[k] = Condition(k, v)
          conditions_in_file.append(k)

      for condition in list(set(persistent_conditions).difference(set(conditions_in_file))):
          dictConditions[condition] = Condition(condition, None)

      def convert_to_entries(data):
          for k, v in data.items():
              print(k, v)
              if type(v) in (int, float, bool, str):
                  data[k] = Entry(k, v)
              elif isinstance(v, dict):
                  data[k] = convert_to_entries(v)
          return data

      self.data = convert_to_entries(self.data)

  def get(self, path, default=None):
      path = path[1:]
      cur = self.data
      for p in path:
          if isinstance(cur, list) and p.isdigit():
              return cur[int(p)]
          if p not in cur:
              return default
          cur = cur[p]
      return cur

  def get_value(self, path, default=None):
      entry = self.get(path, default)
      if isinstance(entry, Entry):
          return entry.value
      return entry

  def set(self, path, value):
      path = path[1:]
      cur = self.data
      for p in path:
          if isinstance(cur, list) and p.isdigit():
              cur[int(p)] = value
              return True
          if p not in cur:
              return False
          if type(cur[p]) in (int, str, float, bool):
              cur[p] = value
              return True
          elif isinstance(cur[p], Entry):
              cur[p].set(value)
              return True
          elif type(cur[p]) in (list, dict):
              cur = cur[p]
          else:
              raise Exception(f'{type(cur[p])}')
      return False

  def save(self, fn):
      json.dump(self.data, open(fn, 'w'))


#  from .enums import SignalEnum, DeathTypeEnum, StartupPopupsFlag, FrequencyEnum
#
#  class ShipLogFactSave:
    #  def __init__(self, id_: str, revealOrder: int =-1, read: bool = False, newlyRevealed: bool = False):
        #  self.id = id_
        #  self.revealOrder = revealOrder
        #  self.read = read
        #  self.newlyRevealed = newlyRevealed
#
    #  @classmethod
    #  def from_dict(cls, data):
        #  return cls(data['id'], data['revealOrder'], data['read'], data['newlyRevealed'])
#
    #  def __repr__(self):
        #  return f'ShipLogFactSave(id={self.id!r}, revealOrder={self.revealOrder}, read={self.read}, newlyRevealed={self.newlyRevealed})'
#
#  class GameSave:
    #  def __init__(self):
        #  self.loopCount: int = 1
        #  self.knownFrequencies = [True, False, False, False, False, False, False]
        #  self.knownSignals: dict[SignalEnum, bool] = {}
        #  self.dictConditions: dict[str, Tristate] = {}
        #  self.shipLogFactSaves: dict[str, ShipLogFactSave] = {}
        #  self.newlyRevealedFactIDs: list[str] = []
        #  self.lastDeathType: DeathTypeEnum = DeathTypeEnum.DEFAULT
        #  self.burnedMarshmallowEaten: int = 0
        #  self.fullTimeloops: int = 0 # uint
        #  self.perfectMarshmallowsEaten: int = 0 # uint
        #  self.warpedToTheEye: bool = False
        #  self.secondsRemainingOnWarp: float = 0.0
        #  self.loopCountOnParadox: int = 0
        #  self.shownPopups: StartupPopupsFlag = StartupPopupsFlag.NONE
        #  self.version: str = "NONE"
        #  self.ps5Activity_canResumeExpedition: bool = False
        #  self.ps5Activity_availableShipLogCards: list[str] = []
        #  self.didRunInitGammaSetting: bool = False
#
    #  @classmethod
    #  def from_json(cls, json: Union[str, TextIOBase]):
        #  save = cls()
        #  if isinstance(json, TextIOBase):
            #  json = json.read()
#
        #  data = loads(json)
        #  save.loopCount = data['loopCount']
        #  save.knownFrequencies = data['knownFrequencies']
        #  for k, v in data['knownSignals'].items():
            #  save.knownSignals[SignalEnum(int(k))] = v
#
        #  for condition in persistent_conditions:
            #  save.dictConditions[condition] = Tristate(data['dictConditions'].get(condition, None))
#
        #  for k, v in data['shipLogFactSaves'].items():
            #  save.shipLogFactSaves[k] = ShipLogFactSave.from_dict(v)
#
        #  save.newlyRevealedFactIDs = data['newlyRevealedFactIDs']
        #  save.lastDeathType = DeathTypeEnum(data['lastDeathType'])
        #  save.burnedMarshmallowEaten = data['burnedMarshmallowEaten']
        #  save.fullTimeloops = data['fullTimeloops']
        #  save.perfectMarshmallowsEaten = data['perfectMarshmallowsEaten']
        #  save.warpedToTheEye = data['warpedToTheEye']
        #  save.secondsRemainingOnWarp = data['secondsRemainingOnWarp']
        #  save.loopCountOnParadox = data['loopCountOnParadox']
        #  save.shownPopups = StartupPopupsFlag(data['shownPopups'])
        #  save.version = data['version']
        #  save.ps5Activity_canResumeExpedition = data['ps5Activity_canResumeExpedition']
        #  save.ps5Activity_availableShipLogCards= data['ps5Activity_availableShipLogCards']
        #  save.didRunInitGammaSetting = data['didRunInitGammaSetting']
#
        #  return save
#
#
    #  def __repr__(self):
        #  out = 'GameSave('
        #  out += f'loopCount={self.loopCount}, knownFrequencies={{...}}, '
        #  out += f'knownSignals={{...}}, dictConditions={{...}}, shipLogFactSaves={{...}}, '
        #  out += f'self.newlyRevealedFactIDs = [...], lastDeathType={self.lastDeathType}, '
        #  out += f'burnedMarshmallowEaten={self.burnedMarshmallowEaten}, fullTimeloops={self.fullTimeloops}, '
        #  out += f'perfectMarshmallowsEaten={self.perfectMarshmallowsEaten}, warpedToTheEye={self.warpedToTheEye}, '
        #  out += f'secondsRemainingOnWarp={self.secondsRemainingOnWarp}, loopCountOnParadox={self.loopCountOnParadox}, '
        #  out += f'shownPopups={self.shownPopups}, version={self.version}'
        #  out += ')'
        #  return out
#
#  from pprint import PrettyPrinter
#
#  if isinstance(getattr(PrettyPrinter, '_dispatch'), dict):
    #  def pprint_GameSave(printer, object, stream, indent, allowance, context, level):
        #  stream.write('GameSave(\n')
        #  ipl = printer._indent_per_level + 1
        #  indent += printer._indent_per_level#len(GameSave.__name__)
        #  stream.write(' ' * ipl + f'loopCount: {object.loopCount}\n')
#
        #  stream.write(' ' * ipl + 'knownFrequencies:\n')
        #  max_len = max(len(x.name) for x in FrequencyEnum)
        #  for n, v in enumerate(object.knownFrequencies):
            #  stream.write(' ' * (ipl*2))
            #  stream.write(f'{FrequencyEnum(n).name.ljust(max_len)}: {v}\n')
#
        #  stream.write(' ' * ipl + 'knownSignals:\n')
        #  max_len = max(len(x.name) for x in object.knownSignals.keys())
        #  for k, v in object.knownSignals.items():
            #  stream.write(' ' * (ipl*2))
            #  stream.write(f'{k.name.ljust(max_len)}: {v}\n')
#
        #  stream.write(' ' * ipl + 'dictConditions:\n')
        #  max_len = max(len(x) for x in object.dictConditions.keys())
        #  for k, v in object.dictConditions.items():
            #  stream.write(' ' * (ipl*2))
            #  stream.write(f'{k.ljust(max_len)}: {v}\n')
#
        #  stream.write(' ' * ipl + 'shipLogFactSaves:\n')
        #  max_len = max(len(x) for x in object.dictConditions.keys())
        #  items = list(object.shipLogFactSaves.items())
        #  items.sort(key=lambda x:(x[1].revealOrder, x[0]))
        #  for k, v in items:
            #  stream.write(' ' * (ipl*2))
            #  read = ' read' if v.read else ''
            #  newlyRevealed = ' newlyRevealed' if v.newlyRevealed else ''
            #  stream.write(f'{k.ljust(max_len)}: revealOrder={v.revealOrder:<3}{read}{newlyRevealed}\n')
#
        #  stream.write(' ' * ipl + f'lastDeathType: {object.lastDeathType}\n')
        #  stream.write(' ' * ipl + f'burnedMarshmallowEaten: {object.burnedMarshmallowEaten}\n')
        #  stream.write(' ' * ipl + f'fullTimeloops: {object.fullTimeloops}\n')
        #  stream.write(' ' * ipl + f'perfectMarshmallowsEaten: {object.perfectMarshmallowsEaten}\n')
        #  stream.write(' ' * ipl + f'warpedToTheEye: {object.warpedToTheEye}\n')
        #  stream.write(' ' * ipl + f'secondsRemainingOnWarp: {object.secondsRemainingOnWarp}\n')
        #  stream.write(' ' * ipl + f'loopCountOnParadox: {object.loopCountOnParadox}\n')
        #  stream.write(' ' * ipl + f'shownPopups: {object.shownPopups}\n')
        #  stream.write(' ' * ipl + f'version: {object.version}\n')
#
        #  stream.write(')')
    #  PrettyPrinter._dispatch[GameSave.__repr__] = pprint_GameSave
