#!/usr/bin/env python

from typing import Optional

from rich.highlighter import ReprHighlighter
from rich.text import Text

highlighter = ReprHighlighter()


def color_bool(val: bool, /, align_left: int = 0, align_right: int = 0) -> Text:
    text = Text.from_markup(f'[green]{val}[/]') if val else Text.from_markup(f'[red]{val}[/]')
    if align_left:
        text.align('left', align_left)
    if align_right:
        text.align('right', align_right)
    return text


# def entry_to_markup(name: str, data: Unknown) -> Text:
#     if name:
#         return Text.assemble(Text.from_markup(f'[b]{name}[/b]='), highlighter(repr(data)))
#     return Text(repr(data))


# def cmp(a, b) -> int:
#     order = [list, tuple, dict]

#     av = order.index(type(a[1])) if type(a[1]) in order else -1
#     bv = order.index(type(b[1])) if type(b[1]) in order else -1

#     if av == bv:
#         if False:  # and isinstance(a[1], dict) and 'revealOrder' in a[1]:
#             av = a[1]['revealOrder']
#             bv = b[1]['revealOrder']
#         else:
#             av = a[0]
#             bv = b[0]
#             if av.isdigit() and bv.isdigit():
#                 av = int(av)
#                 bv = int(bv)

#     r = -1 if av < bv else (1 if av > bv else 0)
#     #  open('out.log', 'a+').write(f'{a}|{av} ? {b}|{bv} -> {r}\n')
#     return r


class Tristate:
    def __init__(self, value: Optional[bool] = None) -> None:
        if value not in (True, False, None):
            raise ValueError('Value must be True, False, or None')
        self.value = value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Tristate):
            return self.value == other.value
        return self.value == other

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __bool__(self) -> bool:
        raise TypeError('Tristate cannot be used as a bool')

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f'Tristate({self.value})'
