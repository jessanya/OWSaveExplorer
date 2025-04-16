#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional
from enum import Enum
from bs4 import Tag

class LocationEnum(Enum):
    Default=0
    LocationA=1
    LocationB=2

class TextBlock:
    
    def __init__(self, idnum: int, text: str, parentID: Optional[int]=None, location: LocationEnum=LocationEnum.Default, defaultFontOverride: bool=False):
        self.id = idnum
        self.text = text
        self.parentID = parentID
        self.location = location
        self.defaultFontOverride = defaultFontOverride

    @classmethod
    def from_tag(cls, tag: Tag):
        if not tag:
            return None
        idnum = int(tag.select_one('ID').text)
        text = tag.select_one('Text').text.strip().encode('raw_unicode_escape').decode('unicode_escape')

        parentID = tag.select_one('ParentID')
        if parentID:
            parentID = int(parentID.text)

        location = LocationEnum.Default
        if tag.select_one('LocationA'):
            location = LocationEnum.LocationA
        elif tag.select_one('LocationB'):
            location = LocationEnum.LocationB

        defaultFontOverride = bool(tag.select_one('DefaultFontOverride'))

        return cls(idnum, text, parentID, location, defaultFontOverride)

    def __repr__(self):
        out = f'TextBlock(id={self.id!r}, text={self.text!r}, parentID={self.parentID!r})'
        if self.location != LocationEnum.Default:
            out += f', location={self.location!r}'
        if self.defaultFontOverride:
            out += f', defaultFontOverride={self.defaultFontOverride!r}'
        out += ')'
        return out

class RevealFact:
    def __init__(self, factID: str, conditions: Optional[list[int]]):
        self.factID = factID
        self.conditions = conditions if conditions is not None else []

    @classmethod
    def from_tag(cls, tag):
        if not tag:
            return None
        factID = tag.select_one('FactID').text.strip()
        conditions = tag.select_one('Condition')
        if conditions:
            conditions = [int(x) for x in conditions.text.split(',') if x]
        else:
            conditions = []

        return cls(factID, conditions)

    def __repr__(self):
        return f'RevealFact(factID={self.factID!r}, conditions={self.conditions!r})'

class ShipLogConditions:
    def __init__(self, facts: list[RevealFact], location: LocationEnum = LocationEnum.Default):
        self.facts = facts
        self.location = location

    @classmethod
    def from_tag(cls, tag):
        if not tag:
            return None
        facts = [RevealFact.from_tag(tag) for tag in tag.select('RevealFact')]
        location = LocationEnum.Default
        if tag.select_one('LocationA'):
            location = LocationEnum.LocationA
        elif tag.select_one('LocationB'):
            location = LocationEnum.LocationB

        return cls(facts, location)

    def __repr__(self):
        return f'ShipLogConditions(facts={self.facts!r}, location={self.location!r})'

class NomaiObject:
    def __init__(self, textblocks: list[TextBlock], shipLogConditions: Optional[ShipLogConditions]=None):
        self.textblocks = textblocks
        self.shipLogConditions = shipLogConditions

    @classmethod
    def from_tag(cls, tag: Tag):
        textblocks = [TextBlock.from_tag(tag) for tag in tag.select('TextBlock')]
        shipLogConditions = ShipLogConditions.from_tag(tag.select_one('ShipLogConditions'))

        return cls(textblocks, shipLogConditions)

    def __repr__(self):
        return f'NomaiObject(textblocks={self.textblocks!r}, shipLogConditions={self.shipLogConditions!r})'

