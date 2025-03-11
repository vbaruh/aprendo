import os
import reflex as rx

import threading
import logging

from typing import List

from aprendo.translations.csv import CsvTranslations
from aprendo.translations.types import TranslationDirection, TranslationIdRange


logger = logging.getLogger(__name__)

thread_state = threading.local()


def _translations() -> CsvTranslations:
    if hasattr(thread_state, 'csv') and thread_state.csv:
        return thread_state.csv

    csv_dir = os.environ.get('APRENDO_CSV_DIR', './')
    csv_path = os.path.join(csv_dir, 'translations.csv')

    csv = CsvTranslations(csv_path)
    csv.load_translations()
    thread_state.csv = csv
    csv.dump_db_info()

    return csv


class Translation(rx.Base):
    id: str
    source_lang: str
    target_lang: str


class TranslationAttempt(rx.Base):
    source_word: str
    user_translation: str
    is_correct: bool
    expected_translations: List[str]


class TranslationState(rx.State):
    """The translation exercise state."""
    direction: TranslationDirection = TranslationDirection.SP_TO_BG
    current_word: str = ''
    user_input: str = ''
    attempts: List[TranslationAttempt] = []
    _has_checked_translation: bool = True
    show_settings: bool = False
    translation_ranges: str = ''
    translation_ranges_error: str = ''
    parsed_id_ranges: List[TranslationIdRange] = None

    @rx.var
    def translations(self) -> List[Translation]:
        """Return list of all translations."""
        return [
            Translation(id=translation[0], source_lang=translation[1], target_lang=translation[2])
            # {'id': translation[0], 'source_lang': translation[1], 'target_lang': translation[2]}
            for translation in _translations().get_translations('es', 'bg')
        ]

    @rx.var(cache=False)
    def current_word_checked(self) -> bool:
        """Return whether the current word has been checked with the Check Translation button."""
        return self._has_checked_translation

    def change_direction(self, new_direction: str):
        """Change the translation direction."""
        self.direction = TranslationDirection(new_direction)
        self.next_word()

    @rx.event
    def check_translation(self):
        """Check if the user's translation is correct."""
        if self._has_checked_translation:
            self.next_word()
            return

        source = self.current_word
        if self.direction == TranslationDirection.SP_TO_BG:
            expected = _translations().get_bulgarian_translations(source)
        else:
            expected = _translations().get_spanish_translations(source)

        if self.user_input == '':
            self.attempts.insert(0, TranslationAttempt(
                source_word=source,
                user_translation='(skipped)',
                is_correct=False,
                expected_translations=expected
            ))
        else:
            logger.debug('source: %s, expected: %s', source, expected)
            is_correct = self.user_input.lower().strip() in [t.lower() for t in expected]

            self.attempts.insert(0, TranslationAttempt(
                source_word=source,
                user_translation=self.user_input,
                is_correct=is_correct,
                expected_translations=expected
            ))

        self._has_checked_translation = True

    @rx.event
    def validate_translation_ranges(self) -> bool:
        """Validate the translation ranges input and create TranslationIdRange objects.

        The input should be either empty or a comma-separated list of ranges.
        Each range should be two integers separated by a dash, with the first integer
        smaller than the second.

        Returns:
            bool: True if the input is valid, False otherwise.
        """
        # Clear any previous parsed ranges
        temp_id_ranges = []

        # Handle empty input
        if not self.translation_ranges.strip():
            self.translation_ranges_error = ''
            self.parsed_id_ranges = None
            return True

        # Split by comma and process each range
        ranges = self.translation_ranges.split(',')
        for range_str in ranges:
            range_str = range_str.strip()
            if not range_str:
                continue

            # Check for dash separator
            if '-' not in range_str:
                self.translation_ranges_error = f'Invalid range format: {range_str}. Expected format: start-end'
                return False

            # Parse and validate start and end values
            try:
                start_str, end_str = range_str.split('-', 1)
                start = int(start_str.strip())
                end = int(end_str.strip())

                # Validate range values
                if start > end:
                    self.translation_ranges_error = f'Invalid range: {start}-{end}. Start must be less than or equal to end.'
                    return False

                if start <= 0 or end <= 0:
                    self.translation_ranges_error = f'Invalid range: {start}-{end}. IDs must be positive.'
                    return False

                # Create and store TranslationIdRange object
                temp_id_ranges.append(TranslationIdRange(start=start, end=end))

            except ValueError:
                self.translation_ranges_error = f'Invalid range format: {range_str}. Expected format: start-end with integer values.'
                return False

        # If we got here, all ranges are valid
        self.translation_ranges_error = ''
        self.parsed_id_ranges = temp_id_ranges
        return True

    @rx.event
    def apply_translation_ranges(self):
        """Apply the validated translation ranges and close the dialog."""
        if self.validate_translation_ranges():
            # Clear any previous error
            self.translation_ranges_error = ''
            # Close the dialog
            self.show_settings = False

    @rx.event
    def next_word(self):
        """Pick the next word randomly."""

        # Pick next word
        source_lang = 'es' if self.direction == TranslationDirection.SP_TO_BG else 'bg'

        # Use the stored parsed_id_ranges
        self.current_word = _translations().get_word_for_translation(source_lang, self.parsed_id_ranges)
        self.user_input = ''
        self._has_checked_translation = False

    def set_user_input(self, value: str):
        """Set the user's input."""
        self.user_input = value

    def set_translation_ranges(self, value: str):
        """Set the translation ranges input."""
        self.translation_ranges = value
        # Clear error when user is typing
        if self.translation_ranges_error:
            self.translation_ranges_error = ''


def translation_table() -> rx.Component:
    """Create the translation history table."""
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell('Source Word'),
                rx.table.column_header_cell('Your Translation'),
                rx.table.column_header_cell('Expected Translations'),
            ),
        ),
        rx.table.body(
            rx.foreach(
                TranslationState.attempts,
                lambda attempt: rx.table.row(
                    rx.table.cell(attempt.source_word),
                    rx.table.cell(
                        rx.hstack(
                            rx.cond(
                                attempt.is_correct,
                                rx.icon('badge-check', color='green'),
                                rx.icon('badge-x', color='red'),
                            ),
                            attempt.user_translation,
                        )
                    ),
                    rx.table.cell(
                        rx.hstack(
                            rx.foreach(
                                attempt.expected_translations,
                                lambda trans: rx.text(trans + ', '),
                            )
                        )
                    ),
                ),
            ),
        ),
        width="100%",
    )


def translation_container() -> rx.Component:
    """Create a scrollable table for translations."""
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell('ID'),
                rx.table.column_header_cell('Spanish'),
                rx.table.column_header_cell('Bulgarian'),
            ),
        ),
        rx.table.body(
            rx.foreach(
                TranslationState.translations,
                lambda translation: rx.table.row(
                    rx.table.cell(translation.id),
                    rx.table.cell(translation.source_lang),
                    rx.table.cell(translation.target_lang),
                ),
            ),
        ),
        width='100%',
    )


def translation_settings_dialog() -> rx.Component:
    """Create the translation settings dialog with translations table."""
    return rx.dialog.root(
        rx.dialog.trigger(rx.button('Settings')),
        rx.dialog.content(
            rx.dialog.title('Translation Settings'),
            rx.dialog.description('List one or more translation ranges in the format 1-10,240-300,...'),
            rx.flex(
                # Fixed header section
                rx.flex(
                    rx.vstack(
                        rx.input(
                            value=TranslationState.translation_ranges,
                            on_change=TranslationState.set_translation_ranges,
                            placeholder='e.g., 1-10,20-30',
                            width='100%',
                        ),
                        rx.cond(
                            TranslationState.translation_ranges_error != '',
                            rx.text(
                                TranslationState.translation_ranges_error,
                                color='red',
                                font_size='0.8em',
                            ),
                            rx.text(
                                'Selected ranges: ' + TranslationState.translation_ranges,
                                font_size='0.8em',
                            ),
                        ),
                        width='90%',
                        align_items='start',
                        spacing='1',
                    ),
                    rx.hstack(
                        rx.button(
                            'Apply',
                            on_click=TranslationState.apply_translation_ranges,
                        ),
                        rx.dialog.close(rx.button('Close')),
                        spacing='2',
                    ),
                    direction='row',
                    justify='between',
                    align_items='start',
                    width='100%',
                    padding='4',
                    border_bottom='1px solid #eaeaea',
                    position='sticky',
                    top='0',
                    z_index='1',
                ),
                # Scrollable content section
                rx.box(
                    translation_container(),
                    width='100%',
                    overflow='auto',
                    flex='1',
                    padding='4',
                ),
                direction='column',
                width='100%',
                height='80vh',
                overflow='hidden',
            ),
            width='100%',
            height='80vh',
            max_width='90vw',
        ),
    )


def translation_page():
    """The translation exercise page."""
    return rx.vstack(
        rx.heading('Translation Exercise', size='3'),
        rx.select(
            items=[direction.value for direction in TranslationDirection],
            placeholder='Select translation direction',
            value=TranslationState.direction,
            on_change=TranslationState.change_direction,
            width='100%',
        ),
        rx.divider(),
        rx.text('Translate:', font_weight='bold'),
        rx.heading(TranslationState.current_word, size='4'),
        rx.form(
            rx.input(
                value=TranslationState.user_input,
                on_change=TranslationState.set_user_input,
                placeholder='Enter translation',
                width='100%',
            ),
            rx.vstack(
                rx.cond(
                    ~TranslationState.current_word_checked,
                    rx.button(
                        'Check Translation',
                        type='submit',
                        color_scheme='blue',
                    ),
                    rx.button(
                        'Next Word',
                        type='submit',
                        color_scheme='green',
                    ),
                ),
                translation_settings_dialog(),
                rx.cond(
                    TranslationState.translation_ranges != '',
                    rx.text(
                        'Selected ranges: ' + TranslationState.translation_ranges,
                        font_size='0.8em',
                    ),
                ),
            ),
            on_submit=TranslationState.check_translation,
            width='100%',
        ),
        rx.divider(),
        translation_table(),
        spacing='4',
        align_items='stretch',
        width='100%',
        max_width='600px',
        padding='4',
    )
