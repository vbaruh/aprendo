import csv
from .types import Translation, TranslationDirection


def load_from_csv(path: str) -> list[Translation]:
    result = []
    with open(path, 'rt', encoding='utf-8', newline='') as f:
        reader = csv.reader(f, delimiter=',', quotechar='"')
        for row in reader:
            if len(row) != 2:
                continue
            raw_word, raw_translations = row
            raw_word = raw_word.strip()
            raw_translations = raw_translations.strip()

            raw_translations = raw_translations.replace('/глагол', '')

            result.append(
                Translation(TranslationDirection.SP_TO_BG, raw_word, raw_translations.split(','))
            )


