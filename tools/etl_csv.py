import csv
import sys
from typing import Optional, List, Tuple, Callable
from pathlib import Path
from io import StringIO


def split_by_delimiter(delimiter: str) -> Callable[[Tuple[str, str]], Optional[List[Tuple[str, str]]]]:
    '''Create a function that splits translations by the given delimiter.
    Only splits when both Spanish and Bulgarian have the same number of delimited items.

    Args:
        delimiter: The delimiter to split by (e.g., ' / ' or ', ')

    Returns:
        A function that takes a translation pair and returns a list of split pairs
    '''
    def _split(row: Tuple[str, str]) -> Optional[List[Tuple[str, str]]]:
        spanish, bulgarian = row

        # Skip if delimiter not in both parts
        if delimiter not in spanish or delimiter not in bulgarian:
            return None

        # Split both parts
        spanish_words = [word.strip() for word in spanish.split(delimiter)]
        bulgarian_words = [word.strip() for word in bulgarian.split(delimiter)]

        # Only process if we have the same number of items in both languages
        if len(spanish_words) != len(bulgarian_words):
            return None

        # Create pairs maintaining the order
        return list(zip(spanish_words, bulgarian_words))

    return _split


def split_by_slash(row: Tuple[str, str]) -> Optional[List[Tuple[str, str]]]:
    '''Split translations that use forward slash to separate multiple meanings.'''
    spanish, bulgarian = row
    if '/' not in bulgarian:
        return None

    translations = [trans.strip() for trans in bulgarian.split('/')]
    return [(spanish.strip(), trans) for trans in translations]


def split_spanish_gender_suffix(row: Tuple[str, str]) -> Optional[List[Tuple[str, str]]]:
    '''Handle Spanish adjectives with gender suffix patterns:
    - Format 1: 'word/a' (e.g., 'variado/a')
    - Format 2: 'word, -a' (e.g., 'cansado, -a')
    Creates both masculine and feminine forms. Skips entries where Bulgarian is "-а".'''
    spanish, bulgarian = row

    # Skip if Bulgarian translation is '-а'
    if bulgarian == '-а':
        return None

    # Try Format 1: word/a
    if spanish.endswith('o/a'):
        base = spanish[:-3]
        return [
            (base + 'o', bulgarian),  # masculine
            (base + 'a', bulgarian),  # feminine
        ]

    # Try Format 2: word, -a
    if spanish.endswith(', -a'):
        base = spanish[:-4]
        return [
            (base, bulgarian),  # masculine
            (base[:-1] + 'a', bulgarian),  # feminine
        ]

    return None


def clean_verb_conjugation(row: Tuple[str, str]) -> Optional[List[Tuple[str, str]]]:
    '''Clean verb conjugations by removing pronouns and keeping only the verb forms.
    Handles both regular and reflexive verbs.'''
    spanish, bulgarian = row

    # Skip if it's an infinitive form (ending in 'r' or 'rse')
    if spanish.endswith('r'):
        return None

    # Common Spanish pronouns to remove
    pronouns = [
        'yo ',
        'tú ',
        'él/ella',
        'él / ella / usted ',
        'nosotros / nosotras ',
        'vosotros / vosotras ',
        'ellos / ellas / ustedes ',
        'nosotros/as ',
        'vosotros/as ',
        'ellos/as '
    ]

    # Bulgarian pronouns to remove
    bg_pronouns = [
        'аз ',
        'ти ',
        'той / тя / Вие',
        'той/тя',
        'той ',
        'тя ',
        'Вие ',
        'ние ',
        'вие ',
        'те / Вие (мн.ч.) ',
        'те ',
        'Вие (мн.ч.) '
    ]

    # Remove Spanish pronouns
    cleaned_spanish = spanish
    for pronoun in pronouns:
        if cleaned_spanish.startswith(pronoun):
            cleaned_spanish = cleaned_spanish[len(pronoun):]
            break

    # Remove Bulgarian pronouns
    cleaned_bulgarian = bulgarian
    for pronoun in bg_pronouns:
        if cleaned_bulgarian.startswith(pronoun):
            cleaned_bulgarian = cleaned_bulgarian[len(pronoun):]
            break

    if cleaned_spanish == spanish and cleaned_bulgarian == bulgarian:
        return None

    return [(cleaned_spanish.strip(), cleaned_bulgarian.strip())]


def split_by_comma(row: Tuple[str, str]) -> Optional[List[Tuple[str, str]]]:
    '''Split translations that use comma to separate multiple meanings.'''
    spanish, bulgarian = row
    if ',' not in bulgarian:
        return None

    translations = [trans.strip() for trans in bulgarian.split(',')]
    return [(spanish.strip(), trans) for trans in translations]


def clean_verb_markers(row: Tuple[str, str]) -> Optional[List[Tuple[str, str]]]:
    '''Remove verb markers like '/глагол' and clean up the translation.'''
    spanish, bulgarian = row
    if '/глагол' not in bulgarian:
        return None

    cleaned = bulgarian.replace('/глагол', '').strip()
    return [(spanish.strip(), cleaned)]


def basic_cleanup(row: Tuple[str, str]) -> Optional[List[Tuple[str, str]]]:
    '''Basic cleanup of strings - strip whitespace and remove empty translations.'''
    spanish, bulgarian = row
    spanish = spanish.strip()
    bulgarian = bulgarian.strip()

    if not spanish or not bulgarian:
        return None

    return [(spanish, bulgarian)]


def transform_csv(input_path: str, output_file_handler: StringIO, transformations: List[Callable]):
    '''Transform CSV file using a sequence of transformation functions.

    Args:
        input_path: Path to input CSV file
        output_path: Path to output CSV file
        transformations: List of transformation functions to apply

    Each transformation function should:
    - Take a tuple of (spanish, bulgarian) strings
    - Return either None (if transformation doesn't apply) or
      a list of one or more (spanish, bulgarian) tuples
    '''
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f'Input file not found: {input_path}')

    results = []

    with open(input_path, 'r', encoding='utf-8', newline='') as f_in:
        reader = csv.reader(f_in, delimiter=',', quotechar='"')
        next(reader)  # Skip header row

        for row in reader:
            if len(row) != 2:
                continue

            current_pairs = [(row[0], row[1])]
            new_pairs = []

            # Apply each transformation to all current pairs
            for transform in transformations:
                for pair in current_pairs:
                    result = transform(pair)
                    if result is not None:
                        new_pairs.extend(result)

                if new_pairs:
                    current_pairs = new_pairs
                    new_pairs = []

            results.extend(current_pairs)

    # filter out "-а" translations
    results = [r for r in results if r[1] not in ['-а', 'а'] ]

    # Write transformed results

    writer = csv.writer(output_file_handler)
    writer.writerow(['Spanish', 'Bulgarian'])  # Write header
    writer.writerows(results)


def main():
    input_file = './data/spanish_to_bg_2025-03-09.csv'

    transformations = [
        clean_verb_markers,          # Then clean verb markers
        clean_verb_conjugation,      # Then clean verb conjugations

        split_spanish_gender_suffix,  # Then handle o/a pattern adjectives
        split_by_delimiter(','),    # First split gender pairs with matching counts
        split_by_delimiter('/'),    # First split gender pairs with matching counts
        split_by_comma,             # Then split other comma-separated translations
        split_by_slash,             # Then split other slash-separated translations
        basic_cleanup,              # Finally clean up the strings
    ]

    # with open(output_path, 'w', encoding='utf-8', newline='') as f_out:
    transform_csv(input_file, sys.stdout, transformations)


if __name__ == '__main__':
    main()
