#!/usr/bin/env python

from enum import IntEnum, IntFlag, auto


class SignalEnum(IntEnum):
    Traveler_Esker = 10
    Traveler_Chert = 11
    Traveler_Riebeck = 12
    Traveler_Gabbro = 13
    Traveler_Feldspar = 14
    Traveler_Nomai = 15
    Traveler_Prisoner = 16
    Quantum_CT_Shard = 20
    Quantum_TH_MuseumShard = 21
    Quantum_TH_GroveShard = 22
    Quantum_BH_Shard = 23
    Quantum_GD_Shard = 24
    Quantum_QM = 25
    EscapePod_CT = 30
    EscapePod_BH = 31
    EscapePod_DB = 32
    WhiteHole_WH = 40
    WhiteHole_SS_Receiver = 41
    WhiteHole_CT_Receiver = 42
    WhiteHole_CT_Experiment = 43
    WhiteHole_TT_Receiver = 44
    WhiteHole_TT_TimeLoopCore = 45
    WhiteHole_TH_Receiver = 46
    WhiteHole_BH_NorthPoleReceiver = 47
    WhiteHole_BH_ForgeReceiver = 48
    WhiteHole_GD_Receiver = 49
    HideAndSeek_Galena = 60
    HideAndSeek_Tephra = 61
    HideAndSeek_Arkose = 62
    RadioTower = 100
    MapSatellite = 101


class FrequencyEnum(IntEnum):
    _ = 0
    Traveler = 1
    Quantum = 2
    EscapePod = 3
    WarpCore = 4
    HideAndSeek = 5
    Radio = 6


class DeathTypeEnum(IntEnum):
    DEFAULT = 0
    IMPACT = auto()
    ASPHYXIATION = auto()
    ENERGY = auto()
    SUPERNOVA = auto()
    DIGESTION = auto()
    BIG_BANG = auto()
    CRUSHED = auto()
    MEDITATION = auto()
    TIME_LOOP = auto()
    LAVA = auto()
    BLACK_HOLE = auto()
    DREAM = auto()
    DREAM_EXPLOSION = auto()
    CRUSHED_BY_ELEVATOR = auto()


class StartupPopupsFlag(IntFlag):
    NONE = 0
    RESET_INPUTS = 1
    REDUCED_FRIGHTS = 2
    NEW_EXHIBIT = 4
