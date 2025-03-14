import reflex as rx

import logging
from typing import List

from aprendo.components.translation_settings_dialog import TranslationSettingsDialog
from aprendo.translations.types import TranslationDirection, TranslationIdRange
from aprendo.translations.runtime import translations


logger = logging.getLogger(__name__)


class TranslationAttempt(rx.Base):
    translation_id: int
    source_word: str
    user_translation: str
    is_correct: bool
    expected_translations: List[str]


class TranslationState(rx.State):
    """The translation exercise state."""
    direction: rx.Field[TranslationDirection] = rx.field(TranslationDirection.SP_TO_BG)
    current_word: rx.Field[str] = rx.field('')
    user_input: rx.Field[str] = rx.field('')
    attempts: rx.Field[List[TranslationAttempt]] = rx.field([])

    _has_checked_translation: bool = True
    _current_translation_id: int = None

    @rx.var
    def parsed_id_ranges_as_text(self) -> str:
        dlg_state = self.get_state(TranslationSettingsDialog)
        return dlg_state.parsed_id_ranges_as_text

    @rx.var(cache=False)
    def current_word_checked(self) -> bool:
        """Return whether the current word has been checked with the Check Translation button."""
        return self._has_checked_translation

    @rx.event
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

        if self.direction == TranslationDirection.SP_TO_BG:
            expected = translations().get_bulgarian_translations(self.current_word)
        else:
            expected = translations().get_spanish_translations(self.current_word)

        if self.user_input == '':
            self.attempts.insert(0, TranslationAttempt(
                translation_id=self._current_translation_id,
                source_word=self.current_word,
                user_translation='(skipped)',
                is_correct=False,
                expected_translations=expected
            ))
        else:
            logger.debug('source: %s, expected: %s', self.current_word, expected)
            is_correct = self.user_input.lower().strip() in [t.lower() for t in expected]

            self.attempts.insert(0, TranslationAttempt(
                translation_id=self._current_translation_id,
                source_word=self.current_word,
                user_translation=self.user_input,
                is_correct=is_correct,
                expected_translations=expected
            ))

        self._has_checked_translation = True

    @rx.event
    def next_word(self):
        """Pick the next word randomly."""

        source_lang = 'es' if self.direction == TranslationDirection.SP_TO_BG else 'bg'

        used_translation_ids = [a.translation_id for a in self.attempts]

        tsd_state = self.get_state(TranslationSettingsDialog)
        self._current_translation_id, self.current_word = translations().get_word_for_translation(source_lang, tsd_state.parsed_id_ranges, used_translation_ids)
        self.user_input = ''
        self._has_checked_translation = False

    def set_user_input(self, value: str):
        """Set the user's input."""
        self.user_input = value


def translation_attempts_table() -> rx.Component:
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

    tsd = TranslationSettingsDialog.create()
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
                tsd,
                rx.cond(
                    TranslationState.parsed_id_ranges_as_text != '',
                    rx.text(
                        'Selected ranges: ' + TranslationState.parsed_id_ranges_as_text,
                        font_size='0.8em',
                    ),
                ),
            ),
            on_submit=TranslationState.check_translation,
            width='100%',
        ),
        rx.divider(),
        translation_attempts_table(),
        spacing='4',
        align_items='stretch',
        width='100%',
        max_width='600px',
        padding='4',
    )
