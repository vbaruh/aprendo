import reflex as rx
from typing import List, Dict
from dataclasses import dataclass, field


# Mock data for SPARQL results
MOCK_SEARCH_RESULTS = [
    {"id": "1", "label": "Hello (English)", "uri": "http://example.org/hello-en"},
    {"id": "2", "label": "Bonjour (French)", "uri": "http://example.org/bonjour-fr"},
    {"id": "3", "label": "Hola (Spanish)", "uri": "http://example.org/hola-es"},
    {"id": "4", "label": "Ciao (Italian)", "uri": "http://example.org/ciao-it"},
]


@dataclass
class SearchResultItem:
    id: str
    label: str
    uri: str


class CollectionState(rx.State):
    """State for managing translation collections."""

    # Step tracking
    current_step: int = 1  # 1 = naming, 2 = member management

    # Collection details
    collection_name: str = ""

    # Search and results
    search_query: str = ""
    search_results: List[SearchResultItem] = []

    # Selected items
    selected_search_items: List[str] = []  # IDs from search results
    collection_members: List[Dict] = []  # Actually added items

    def next_step(self):
        """Move to the member management step."""
        if not self.collection_name.strip():
            return rx.window_alert("Please enter a collection name")
        self.current_step = 2

    def back_step(self):
        """Go back to naming step."""
        self.current_step = 1

    def search_translations(self):
        """Mock SPARQL search."""
        if not self.search_query.strip():
            return rx.window_alert("Please enter a search term")
        # Mock search by filtering mock data
        self.search_results = [
            SearchResultItem(
                id=r["id"],
                label=r["label"],
                uri=r["uri"],
            ) for r in MOCK_SEARCH_RESULTS
            if self.search_query.lower() in r["label"].lower()
        ]

    def toggle_search_item(self, item_id: str):
        """Toggle an item in the selected_search_items list."""
        if item_id in self.selected_search_items:
            self.selected_search_items.remove(item_id)
        else:
            self.selected_search_items.append(item_id)

    def add_selected_to_collection(self):
        """Add selected items to collection members."""
        new_members = [
            item for item in MOCK_SEARCH_RESULTS
            if item["id"] in self.selected_search_items
            and item not in self.collection_members
        ]
        self.collection_members.extend(new_members)
        self.selected_search_items = []

    def remove_from_collection(self, item_id: str):
        """Remove an item from collection members."""
        self.collection_members = [
            item for item in self.collection_members
            if item["id"] != item_id
        ]

def collection_name_step():
    """First step - naming the collection."""
    return rx.vstack(
        rx.heading("Create Translation Collection", size='2'),
        rx.text("Step 1: Name your collection"),
        rx.input(
            placeholder="Enter collection name...",
            value=CollectionState.collection_name,
            on_change=CollectionState.set_collection_name,
            width="100%",
        ),
        rx.button(
            "Next",
            on_click=CollectionState.next_step,
            width="100%",
        ),
        width="100%",
        max_width="600px",
        spacing="4",
        padding="4",
    )

def search_panel():
    """Search panel for finding translations."""
    return rx.vstack(
        rx.hstack(
            rx.input(
                placeholder="Search translations...",
                value=CollectionState.search_query,
                on_change=CollectionState.set_search_query,
                flex="1",
            ),
            rx.button(
                "Search",
                on_click=CollectionState.search_translations,
            ),
            width="100%",
        ),
        rx.box(
            rx.foreach(
                CollectionState.search_results,
                lambda item: rx.checkbox(
                    item.label,
                    # is_checked=rx.cond(
                    #     item.id.in_(CollectionState.selected_search_items),
                    #     True,
                    #     False
                    # ),
                    on_change=lambda: CollectionState.toggle_search_item(item.id),
                )
            ),
            padding="4",
            border="1px solid",
            border_color="gray.200",
            border_radius="md",
            width="100%",
            min_height="200px",
        ),
        rx.button(
            "Add Selected",
            on_click=CollectionState.add_selected_to_collection,
            # is_disabled=rx.len(CollectionState.selected_search_items) == 0,
        ),
        width="100%",
        spacing="4",
    )

def collection_members_panel():
    """Panel showing current collection members."""
    return rx.vstack(
        rx.heading("Collection Members", size='3'),
        rx.box(
            rx.foreach(
                CollectionState.collection_members,
                lambda item: rx.hstack(
                    rx.text(item["label"]),
                    rx.spacer(),
                    rx.button(
                        "Remove",
                        on_click=lambda: CollectionState.remove_from_collection(item.id),
                        size="1",
                        color_scheme="red",
                    ),
                    width="100%",
                    padding="2",
                )
            ),
            border="1px solid",
            border_color="gray.200",
            border_radius="md",
            width="100%",
            min_height="200px",
            padding="4",
        ),
        width="100%",
        spacing="4",
    )

def member_management_step():
    """Second step - managing collection members."""
    return rx.vstack(
        rx.heading(
            rx.hstack(
                rx.button(
                    "← Back",
                    on_click=CollectionState.back_step,
                    variant="ghost",
                ),
                rx.heading(f"Collection: {CollectionState.collection_name}", size='2'),
            ),
            width="100%",
        ),
        rx.text("Step 2: Add or remove collection members"),
        rx.grid(
            search_panel(),
            collection_members_panel(),
            template_columns="repeat(2, 1fr)",
            gap=4,
            width="100%",
        ),
        width="100%",
        max_width="1200px",
        spacing="4",
        padding="4",
    )

def collections_page():
    """Main page component."""
    return rx.center(
        rx.cond(
            CollectionState.current_step == 1,
            collection_name_step(),
            member_management_step(),
        ),
        width="100%",
        min_height="100vh",
        padding="4",
    )
