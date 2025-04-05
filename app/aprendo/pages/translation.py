import os
import reflex as rx

import threading
import logging
import difflib
import enum

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
    if os.path.exists(csv_path):
        csv.load_translations()
    thread_state.csv = csv

    return csv


class Translation(rx.Base):
    id: str
    source_lang: str
    target_lang: str


class TranslationCorrectness(str, enum.Enum):
    CORRECT = 'correct'
    ALMOST = 'almost'
    INCORRECT = 'incorrect'


class DiffOpcode(rx.Base):
    """Represents a single diff operation from difflib's SequenceMatcher."""
    tag: str  # 'replace', 'delete', 'insert', or 'equal'
    i1: int   # Start index in first sequence
    i2: int   # End index in first sequence
    j1: int   # Start index in second sequence
    j2: int   # End index in second sequence


class TranslationAttempt(rx.Base):
    translation_id: int
    source_word: str
    user_translation: str
    is_correct: TranslationCorrectness
    expected_translations: List[str]
    matching_translation: str = ''
    # Store opcodes as a list of DiffOpcode objects
    diff_opcodes: List[DiffOpcode] = []


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
    _current_translation_id: int = None

    @rx.var
    def has_id_ranges(self) -> bool:
        return self.parsed_id_ranges is not None and len(self.parsed_id_ranges) > 0

    @rx.var
    def display_id_ranges(self) -> str:
        return str(self.parsed_id_ranges) if self.has_id_ranges else ''

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
                translation_id=self._current_translation_id,
                source_word=source,
                user_translation='(skipped)',
                is_correct=TranslationCorrectness.INCORRECT,
                expected_translations=expected,
                matching_translation=''
            ))
        else:
            logger.debug('source: %s, expected: %s', source, expected)
            user_input_lower = self.user_input.lower().strip()
            expected_lower = [t.lower() for t in expected]

            # Check for exact match first
            if user_input_lower in expected_lower:
                matching_idx = expected_lower.index(user_input_lower)
                self.attempts.insert(0, TranslationAttempt(
                    translation_id=self._current_translation_id,
                    source_word=source,
                    user_translation=self.user_input,
                    is_correct=TranslationCorrectness.CORRECT,
                    expected_translations=expected,
                    matching_translation=expected[matching_idx]
                ))
            else:
                # Check for almost match using difflib
                best_match = ''
                best_ratio = 0.0
                threshold = 0.8  # 80% similarity threshold for 'almost' correct


                for translation in expected:
                    ratio = difflib.SequenceMatcher(None, user_input_lower, translation.lower()).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match = translation

                if best_ratio >= threshold:
                    correctness = TranslationCorrectness.ALMOST
                    # Get opcodes for diff visualization
                    matcher = difflib.SequenceMatcher(None, self.user_input.lower(), best_match.lower())
                    # Convert opcodes to a list of DiffOpcode objects
                    diff_opcodes = [DiffOpcode(tag=tag, i1=i1, i2=i2, j1=j1, j2=j2)
                                   for tag, i1, i2, j1, j2 in matcher.get_opcodes()]
                else:
                    correctness = TranslationCorrectness.INCORRECT
                    best_match = ''
                    diff_opcodes = []

                self.attempts.insert(0, TranslationAttempt(
                    translation_id=self._current_translation_id,
                    source_word=source,
                    user_translation=self.user_input,
                    is_correct=correctness,
                    expected_translations=expected,
                    matching_translation=best_match,
                    diff_opcodes=diff_opcodes
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

        used_translation_ids = [a.translation_id for a in self.attempts]
        # Use the stored parsed_id_ranges
        self._current_translation_id, self.current_word = _translations().get_word_for_translation(source_lang, self.parsed_id_ranges, used_translation_ids)
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


def render_diff(user_input: str, correct_translation: str, opcodes: List[DiffOpcode]) -> rx.Component:
    """Render a visual diff between user input and correct translation.

    Args:
        user_input: The user's input translation
        correct_translation: The correct translation
        opcodes: List of DiffOpcode objects from difflib.SequenceMatcher.get_opcodes()

    Returns:
        List of components showing the diff visualization
    """
    # Pre-process opcodes to create components
    # This happens on the backend, so we can use Python conditionals here
    return rx.hstack(
        rx.foreach(
            opcodes,
            lambda opcode: render_diff_component(user_input, correct_translation, opcode)
        ),
        spacing='0'
    )


def render_diff_component(user_input: str, correct_translation: str, opcode: DiffOpcode) -> rx.Component:
    # tag, i1, i2, j1, j2 = opcode.tag, opcode.i1, opcode.i2, opcode.j1, opcode.j2
    return rx.cond(
        opcode.tag == 'replace',
        rx.hstack(
            rx.text(
                user_input[opcode.i1:opcode.i2],
                text_decoration='line-through',
                color='red',
            ),
            rx.text(
                correct_translation[opcode.j1:opcode.j2],
                color='green',
            ),
            spacing='0',
        ),
        rx.cond(
            opcode.tag == 'delete',
            rx.text(
                user_input[opcode.i1:opcode.i2],
                text_decoration='line-through',
                color='red',
            ),
            rx.cond(
                opcode.tag == 'insert',
                rx.text(
                    correct_translation[opcode.j1:opcode.j2],
                    color='green',
                ),
                rx.text(user_input[opcode.i1:opcode.i2]),
            ),
        )
    )


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
                                attempt.is_correct == TranslationCorrectness.CORRECT,
                                rx.icon('badge-check', color='green'),
                                rx.cond(
                                    attempt.is_correct == TranslationCorrectness.ALMOST,
                                    rx.icon('badge-percent', color='yellow'),
                                    rx.icon('badge-x', color='gray'),
                                )
                            ),
                            attempt.user_translation,
                        )
                    ),
                    rx.table.cell(
                        rx.cond(
                            attempt.is_correct == TranslationCorrectness.CORRECT,
                            # For correct answers, show matching translation first and underlined
                            rx.vstack(
                                rx.text(attempt.matching_translation, text_decoration='underline'),
                                rx.foreach(
                                    attempt.expected_translations,
                                    lambda trans: rx.cond(
                                        trans != attempt.matching_translation,
                                        rx.text(trans),
                                    )
                                )
                            ),
                            rx.cond(
                                attempt.is_correct == TranslationCorrectness.ALMOST,
                                # For almost correct answers, show matching translation first with correction hints
                                rx.vstack(
                                    render_diff(attempt.user_translation, attempt.matching_translation, attempt.diff_opcodes),
                                    rx.foreach(
                                        attempt.expected_translations,
                                        lambda trans: rx.cond(
                                            trans != attempt.matching_translation,
                                            rx.text(trans),
                                        )
                                    ),
                                    align_items='start',
                                    spacing='0'
                                ),
                                # For incorrect answers, show all translations normally
                                rx.vstack(
                                    rx.foreach(
                                        attempt.expected_translations,
                                        lambda trans: rx.text(trans),
                                    )
                                )
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
                            rx.cond(
                                TranslationState.has_id_ranges,
                                rx.text(
                                    'Selected ranges: ' + TranslationState.display_id_ranges,
                                    font_size='0.8em',
                                ),
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
                    TranslationState.has_id_ranges,
                    rx.text(
                        'Selected ranges: ' + TranslationState.display_id_ranges,
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
