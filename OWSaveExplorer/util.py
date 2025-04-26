#!/usr/bin/env python

from typing import Optional

from rich.highlighter import ReprHighlighter
from rich.text import Text
from textual.validation import Function, ValidationResult

highlighter = ReprHighlighter()


def color_bool(val: bool, /, align_left: int = 0, align_right: int = 0) -> Text:
    text = Text.from_markup(f'[green]{val}[/]') if val else Text.from_markup(f'[red]{val}[/]')
    if align_left:
        text.align('left', align_left)
    if align_right:
        text.align('right', align_right)
    return text


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


class ValidationWrapper:
    def __init__(self, validator: Function) -> None:
        self.validator = validator

    def validate(self, value: object) -> ValidationResult:
        if self.validator is None:
            return ValidationResult()
        try:
            return self.validator.validate(value)
        except Exception:
            return self.validator.failure()
