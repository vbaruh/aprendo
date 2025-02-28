import reflex as rx
from aprendo.pages.translation import translation_page
from aprendo.pages.numbers import numbers_page


class State(rx.State):
    """The app state."""
    def go_to_translation(self):
        return rx.redirect("/translation")


def navbar():
    """The navigation bar."""
    return rx.box(
        rx.hstack(
            rx.menu.root(
                rx.menu.trigger(
                    rx.icon("menu")
                ),
                rx.menu.content(
                    rx.menu.item(rx.link("Translation", href="/translation")),
                    rx.menu.item(rx.link("Numbers", href="/numbers")),
                ),
            ),
            rx.heading("Aprendo", size="3"),
            # rx.spacer(),
        ),
        width="100%",
        padding="4",
        # bg="white",
        border_bottom="1px solid #eaeaea",
    )


def index():
    """The main page - redirects to translation."""
    return rx.vstack(
        rx.script("window.location.href = '/translation'"),
    )


def app_layout(content: rx.Component):
    """The main app layout."""
    return rx.box(
        navbar(),
        rx.box(
            content,
            padding_top="4",
            display="flex",
            justify_content="center",
        ),
        min_height="100vh",
    )


# Create app and add pages
app = rx.App()
app.add_page(index)
app.add_page(
    lambda: app_layout(translation_page()),
    route="/translation",
)
app.add_page(
    lambda: app_layout(numbers_page()),
    route="/numbers",
)
