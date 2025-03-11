from enum import Enum
from dataclasses import dataclass
from typing import Optional


class Languages(str, Enum):
    SPANISH = 'es'
    BULGARIAN = 'bg'


class TranslationDirection(str, Enum):
    SP_TO_BG = 'Spanish → Bulgarian'
    BG_TO_SP = 'Bulgarian → Spanish'


@dataclass
class TranslationIdRange:
    start: int
    end: int


@dataclass
class Translation:
    direction: TranslationDirection
    word: str
    translations: list[str]
