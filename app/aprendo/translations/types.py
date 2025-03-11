from enum import Enum
from dataclasses import dataclass


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

    def __str__(self) -> str:
        return f'{self.start}-{self.end}'

    def __repr__(self) -> str:
        return f'{self.start}-{self.end}'


@dataclass
class Translation:
    direction: TranslationDirection
    word: str
    translations: list[str]
