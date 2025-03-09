import reflex as rx
from reflex.style import toggle_color_mode
from aprendo.pages.translation import translation_page
from aprendo.pages.numbers import numbers_page
from aprendo.pages.collections import collections_page


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
                    rx.menu.item(rx.link("Collections", href="/collections")),
                ),
            ),
            rx.heading("Aprendo", size="3"),
            rx.spacer(),
            rx.color_mode_cond(
                light=rx.icon('moon', on_click=toggle_color_mode,),
                dark=rx.icon('sun', on_click=toggle_color_mode,),
            ),
        ),
        width="100%",
        padding="4",
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
app = rx.App(
    theme=rx.theme(),
)
app.add_page(index)
app.add_page(
    lambda: app_layout(translation_page()),
    route="/translation",
)
app.add_page(
    lambda: app_layout(numbers_page()),
    route="/numbers",
)
app.add_page(
    lambda: app_layout(collections_page()),
    route="/collections",
)
