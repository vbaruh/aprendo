import os
import reflex as rx

import threading
import logging

from typing import List

from aprendo.translations.csv import CsvTranslations
from aprendo.translations.types import TranslationDirection


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
    def next_word(self):
        """Pick the next word randomly."""

        # Pick next word
        source_lang = 'es' if self.direction == TranslationDirection.SP_TO_BG else 'bg'
        self.current_word = _translations().get_word_for_translation(source_lang)
        self.user_input = ""
        self._has_checked_translation = False

    def set_user_input(self, value: str):
        """Set the user's input."""
        self.user_input = value


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
                    rx.input(width='90%'),
                    rx.dialog.close(rx.button('Close')),
                    direction='row',
                    justify='between',
                    align_items='center',
                    width='100%',
                    padding='4',
                    border_bottom='1px solid #eaeaea',
                    # background_color='white',
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
