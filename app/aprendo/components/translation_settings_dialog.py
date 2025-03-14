import reflex as rx

from typing import List, Tuple

from aprendo.translations.types import TranslationIdRange
from aprendo.translations.runtime import translations


class Translation(rx.Base):
    id: str
    source_lang: str
    target_lang: str


class TranslationSettingsDialog(rx.ComponentState):
    translation_ranges: rx.Field[str] = rx.field('')
    translation_ranges_error: rx.Field[str] = rx.field('')

    parsed_id_ranges: rx.Field[List[TranslationIdRange]] = rx.field([])

    @rx.var(cache=True)
    def translations(self) -> List[Translation]:
        """Return list of all translations."""
        return [
            Translation(id=translation[0], source_lang=translation[1], target_lang=translation[2])
            for translation in translations().get_translations('es', 'bg')
        ]

    @rx.var
    def parsed_id_ranges_as_text(self) -> str:
        return ', '.join([f'{r}' for r in self.parsed_id_ranges])

    @rx.event
    def close_translation_settings_dialog(self):
        """Close the translation settings dialog."""
        self.translation_ranges = self.parsed_id_ranges_as_text
        self.translation_ranges_error = ''

    def set_translation_ranges(self, value: str):
        """Set the translation ranges input."""
        self.translation_ranges = value
        # Clear error when user is typing
        if self.translation_ranges_error:
            self.translation_ranges_error = ''

    def _validate_translation_ranges(self) -> Tuple[bool, str, List[TranslationIdRange]]:
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
            return (True, '', [])

        # Split by comma and process each range
        ranges = self.translation_ranges.split(',')
        for range_str in ranges:
            range_str = range_str.strip()
            if not range_str:
                continue

            # Check for dash separator
            if '-' not in range_str:
                err = f'Invalid range format: {range_str}. Expected format: start-end'
                return (False, err, [])

            # Parse and validate start and end values
            try:
                start_str, end_str = range_str.split('-', 1)
                start = int(start_str.strip())
                end = int(end_str.strip())

                # Validate range values
                if start > end:
                    err = f'Invalid range: {start}-{end}. Start must be less than or equal to end.'
                    return (False, err, [])

                if start <= 0 or end <= 0:
                    err = f'Invalid range: {start}-{end}. IDs must be positive.'
                    return (False, err, [])

                # Create and store TranslationIdRange object
                temp_id_ranges.append(TranslationIdRange(start=start, end=end))

            except ValueError:
                err = f'Invalid range format: {range_str}. Expected format: start-end with integer values.'
                return (False, err, [])

        # If we got here, all ranges are valid
        return (True, '', temp_id_ranges)

    @rx.event
    def apply_translation_ranges(self):
        """Apply the validated translation ranges and close the dialog."""
        success, err, parsed_id_ranges = self._validate_translation_ranges()
        self.translation_ranges_error = err
        if success:
            self.parsed_id_ranges = parsed_id_ranges

    @classmethod
    def _translation_container(cls) -> rx.Component:
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
                    cls.translations,
                    lambda translation: rx.table.row(
                        rx.table.cell(translation.id),
                        rx.table.cell(translation.source_lang),
                        rx.table.cell(translation.target_lang),
                    ),
                ),
            ),
            width='100%',
        )

    @classmethod
    def get_component(cls, **props):
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
                                value=cls.translation_ranges,
                                on_change=cls.set_translation_ranges,
                                placeholder='e.g., 1-10,20-30',
                                width='100%',
                            ),
                            rx.cond(
                                cls.translation_ranges_error != '',
                                rx.text(
                                    cls.translation_ranges_error,
                                    color='red',
                                    font_size='0.8em',
                                ),
                                rx.cond(
                                    cls.parsed_id_ranges_as_text != '',
                                    rx.text(
                                        'Selected ranges: ' + cls.parsed_id_ranges_as_text,
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
                                on_click=cls.apply_translation_ranges,
                                color_scheme='blue',
                            ),
                            rx.dialog.close(rx.button(
                                'Close',
                                on_click=cls.close_translation_settings_dialog,
                                color_scheme='gray',
                            )),
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
                        cls._translation_container(),
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
