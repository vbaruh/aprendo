import reflex as rx
import random

from os import linesep

SPANISH_NUMBERS = {
    0: "cero", 1: "uno", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco",
    6: "seis", 7: "siete", 8: "ocho", 9: "nueve", 10: "diez",
    11: "once", 12: "doce", 13: "trece", 14: "catorce", 15: "quince",
    16: "dieciséis", 17: "diecisiete", 18: "dieciocho", 19: "diecinueve",
    20: "veinte",
    21: 'veintiuno', 22: 'veintidós', 23: 'veintitrés', 24: 'veinticuatro',
    25: 'veinticinco', 26: 'veintiséis', 27: 'veintisiete', 28: 'veintiocho',
    29: 'veintinueve',
    30: "treinta", 40: "cuarenta", 50: "cincuenta",
    60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"
}

SPANISH_HUNDREDS = {
    100: "cien",
    200: "doscientos",
    300: "trescientos",
    400: "cuatrocientos",
    500: "quinientos",
    600: "seiscientos",
    700: "setecientos",
    800: "ochocientos",
    900: "novecientos"
}

SEP = '\u000D'

SPANISH_NUMBER_HINTS = [
    *[f'{k}: {v}' for k, v in SPANISH_NUMBERS.items() if not (k >= 21 and k <= 29)],
    '100: ciento',
    *[f'{k}: {v}' for k, v in SPANISH_HUNDREDS.items()],
    '1000: mil'
]

class Attempt(rx.Base):
    """Represents a single attempt at translating a number to Spanish."""
    number: int
    user_input: str
    correct_answer: str
    is_correct: bool = False


class NumbersState(rx.State):
    """The numbers exercise state."""
    current_number: int = 0
    user_answer: str = ""
    min_value: int = 0
    max_value: int = 9999
    feedback: str = ""
    is_correct: bool = False
    history: list[Attempt] = []

    @rx.var
    def current_number_str(self) -> str:
        return str(self.current_number)

    def convert_to_spanish(self, number: int) -> str:
        """Convert a number to Spanish words."""
        # Handle thousands (1000-9999)
        if number >= 1000:
            thousands = number // 1000
            remainder = number % 1000
            if thousands == 1:
                prefix = "mil"
            else:
                prefix = f"{SPANISH_NUMBERS[thousands]} mil"

            if remainder == 0:
                return prefix
            return f"{prefix} {self.convert_to_spanish(remainder)}"

        # Handle hundreds (100-999)
        if number >= 100:
            hundreds = (number // 100) * 100
            remainder = number % 100

            if hundreds == 100 and remainder > 0:
                prefix = "ciento"
            else:
                prefix = SPANISH_HUNDREDS[hundreds]

            if remainder == 0:
                return prefix
            return f"{prefix} {self.convert_to_spanish(remainder)}"

        # Handle 1-99
        if number in SPANISH_NUMBERS:
            return SPANISH_NUMBERS[number]

        # Handle remaining two-digit numbers
        tens = (number // 10) * 10
        ones = number % 10
        if ones == 0:
            return SPANISH_NUMBERS[tens]
        return f"{SPANISH_NUMBERS[tens]} y {SPANISH_NUMBERS[ones]}"

    def generate_new_number(self):
        """Generate a new random number within the specified range."""
        self.current_number = random.randint(self.min_value, self.max_value)
        self.user_answer = ""
        self.feedback = ""
        self.is_correct = False

    def set_current_number(self, value: str):
        """Set the current number from user input."""
        try:
            number = int(value)
            if 0 <= number <= 9999:
                self.current_number = number
                self.user_answer = ""
                self.feedback = ""
                self.is_correct = False
        except ValueError:
            pass

    def check_answer(self):
        """Check if the user's answer is correct."""
        correct_answer = self.convert_to_spanish(self.current_number)
        if self.user_answer.lower().strip() == correct_answer:
            self.feedback = "¡Correcto! "
            self.is_correct = True
        else:
            self.feedback = f"Incorrect. The correct answer is: {correct_answer}"
            self.is_correct = False

        # Add to history using Attempt class
        self.history.insert(0,
            Attempt(
                number=self.current_number,
                user_input=self.user_answer.lower().strip(),
                correct_answer=correct_answer,
                is_correct=self.is_correct,
            )
        )

    def handle_key_press(self, key: str):
        """Handle key press events."""
        if key == "Enter" and self.user_answer.strip():
            self.check_answer()

    def update_min(self, value: str):
        """Update minimum value."""
        try:
            new_min = int(value)
            if 0 <= new_min <= self.max_value:
                self.min_value = new_min
        except ValueError:
            pass

    def update_max(self, value: str):
        """Update maximum value."""
        try:
            new_max = int(value)
            if new_max >= self.min_value and new_max <= 9999:
                self.max_value = new_max
        except ValueError:
            pass

    def set_user_answer(self, value: str):
        """Set user's answer."""
        self.user_answer = value


def _hints():
    return rx.popover.root(
        rx.popover.trigger(
            rx.button('Hints'),
        ),
        rx.popover.content(
            rx.grid(
                rx.foreach(SPANISH_NUMBER_HINTS, lambda hint: rx.text(hint, size='2')),
                spacing='4',
                width='100%',
                flow="column",
                rows='10'
            ),
        ),
    )


def numbers_page():
    """The numbers exercise page."""
    return rx.vstack(
        rx.heading("Numbers Exercise", size="3"),
        rx.text("Practice writing Spanish numbers! Set your desired range and type the number in Spanish words."),
        rx.text("Supports numbers from 0 to 9999"),

        rx.hstack(
            rx.input(
                placeholder="Min value",
                on_change=NumbersState.update_min,
                value=NumbersState.min_value,
                width="150px",
            ),
            rx.input(
                placeholder="Max value",
                on_change=NumbersState.update_max,
                value=NumbersState.max_value,
                width="150px",
            ),
            rx.button(
                "Generate Random Number",
                on_click=NumbersState.generate_new_number,
                color_scheme="blue",
            ),
            wrap='wrap',
        ),

        rx.vstack(
            rx.vstack(
                rx.text("Number to write:"),
                rx.input(
                    placeholder="Enter a number (0-9999)",
                    on_change=NumbersState.set_current_number,
                    value=NumbersState.current_number_str,
                    type_="number",
                ),
            ),
            rx.text_area(
                placeholder="Type the number in Spanish",
                on_change=NumbersState.set_user_answer,
                on_key_down=NumbersState.handle_key_press,
                value=NumbersState.user_answer,
                width="80%",
            ),
            rx.hstack(
                rx.button(
                    "Check Answer",
                    on_click=NumbersState.check_answer,
                    color_scheme="green",
                ),
                _hints(),
            ),
            rx.text(
                NumbersState.feedback,
                color=rx.cond(
                    NumbersState.is_correct,
                    "green.500",
                    "red.500"
                )
            ),
            # History table
            rx.vstack(
                rx.heading("History", size="4"),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Number"),
                            rx.table.column_header_cell("Your Answer"),
                            rx.table.column_header_cell("Correct Answer"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            NumbersState.history,
                            lambda item: rx.table.row(
                                rx.table.cell(item.number),
                                rx.table.cell(
                                    rx.hstack(
                                        rx.cond(
                                            item.is_correct,
                                            rx.icon("badge-check", color="green"),
                                            rx.icon("badge-x", color="red"),
                                        ),
                                        item.user_input),
                                ),
                                rx.table.cell(item.correct_answer),
                            )
                        )
                    ),
                    width="100%",
                ),
            ),
            width="100%",
            spacing="4",
        ),

        spacing="4",
        align_items="stretch",
        width="100%",
        max_width="800px",  # Increased max width to accommodate the table
        padding="4",
    )
