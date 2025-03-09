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
    _has_checked_translation: bool = False

    # @rx.var(cache=False)
    # def attempts(self) -> List[TranslationAttempt]:
    #     result = [
    #         TranslationAttempt(
    #             source_word=item[1],
    #             user_translation=item[2],
    #             is_correct=item[3],
    #             expected_translations=item[4]
    #         )
    #         for item in _translations().get_translation_history()
    #     ]
    #     return result

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

        if self.user_input == '':
            return

        source = self.current_word
        if self.direction == TranslationDirection.SP_TO_BG:
            expected = _translations().get_bulgarian_translations(source)
        else:
            expected = _translations().get_spanish_translations(source)

        logger.debug('source: %s, expected: %s', source, expected)
        is_correct = self.user_input.lower().strip() in [t.lower() for t in expected]

        self.attempts.append(TranslationAttempt(
            source_word=source,
            user_translation=self.user_input,
            is_correct=is_correct,
            expected_translations=expected
        ))

        self._has_checked_translation = True

    @rx.event
    def next_word(self):
        """Pick the next word randomly."""
        # If there's no input, mark it as incorrect attempt
        if self.current_word and not self._has_checked_translation:
            source = self.current_word
            if self.direction == TranslationDirection.SP_TO_BG:
                expected = _translations().get_bulgarian_translations(source)
            else:
                expected = _translations().get_spanish_translations(source)

            # Insert skipped attempt at the beginning
            self.attempts.insert(0, TranslationAttempt(
                source_word=source,
                user_translation='(skipped)',
                is_correct=False,
                expected_translations=expected
            ))

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
            rx.hstack(
                rx.button(
                    'Check Translation',
                    type='submit',
                    color_scheme='blue',
                ),
                rx.button(
                    'Next Word',
                    type='button',
                    on_click=TranslationState.next_word,
                    color_scheme='green',
                    disabled=rx.cond(
                        TranslationState.user_input != '',
                        rx.cond(TranslationState.current_word_checked, False, True),
                        False
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
