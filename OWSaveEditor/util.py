#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rich.text import Text
from rich.highlighter import ReprHighlighter

highlighter = ReprHighlighter()

def entry_to_markup(name, data):
    if name:
        return Text.assemble( Text.from_markup(f'[b]{name}[/b]='), highlighter(repr(data)) )
    return Text(repr(data))

def cmp(a, b):
    order = [list, tuple, dict]

    av = order.index(type(a[1])) if type(a[1]) in order else -1
    bv = order.index(type(b[1])) if type(b[1]) in order else -1

    if av == bv:
        if False and isinstance(a[1], dict) and 'revealOrder' in a[1]:
            av = a[1]['revealOrder']
            bv = b[1]['revealOrder']
        else:
            av = a[0]
            bv = b[0]
            if av.isdigit() and bv.isdigit():
                av = int(av)
                bv = int(bv)

    r = -1 if av < bv else (1 if av > bv else 0)
    #  open('out.log', 'a+').write(f'{a}|{av} ? {b}|{bv} -> {r}\n')
    return r


class Tristate:
    def __init__(self, value=None):
        if value not in (True, False, None):
            raise ValueError('Value must be True, False, or None')
        self.value = value

    def __eq__(self, other):
        if isinstance(other, Tristate):
            return self.value == other.value
        return self.value == other

    def __ne__(self, other):
       return not self == other

    def __bool__(self):   
       raise TypeError('Tristate cannot be used as a bool')

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f'Tristate({self.value})' 
