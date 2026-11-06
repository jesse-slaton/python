"""Custom widgets for the Package Manager TUI."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.widgets import DataTable, Input, Label, Static

from package_manager import Package


class PackageTable(DataTable):
    """Data table for displaying packages with checkbox selection."""

    BINDINGS = [  # noqa: RUF012  Textual BINDINGS is a framework-defined class attribute, never mutated
        ("space", "toggle_selection", "Toggle Selection"),
        ("ctrl+a", "select_all", "Select All"),
        ("ctrl+d", "deselect_all", "Deselect All"),
    ]

    def __init__(self, show_updates: bool = False, *args, **kwargs) -> None:
        """Initialize the package table.

        Args:
            show_updates: Whether to show the Available column for updates
        """
        super().__init__(*args, **kwargs)
        self.show_updates = show_updates
        self.selected_packages: set[str] = set()
        self.packages: list[Package] = []
        self.cursor_type = "row"

    def on_mount(self) -> None:
        """Set up the table when mounted."""
        self.add_column("☐", width=3, key="checkbox")
        self.add_column("Name", width=30, key="name")
        self.add_column("ID", width=25, key="id")
        self.add_column("Version", width=12, key="version")

        if self.show_updates:
            self.add_column("Available", width=12, key="available")

        self.add_column("Source", width=10, key="source")

    def load_packages(self, packages: list[Package]) -> None:
        """Load packages into the table.

        Args:
            packages: List of packages to display
        """
        self.packages = packages
        self.clear()
        self.selected_packages.clear()

        for pkg in packages:
            checkbox = "☐"
            row_data = [checkbox, pkg.name, pkg.id, pkg.version]

            if self.show_updates:
                row_data.append(pkg.available_version or "")

            row_data.append(pkg.source)

            self.add_row(*row_data, key=pkg.id)

    def action_toggle_selection(self) -> None:
        """Toggle selection of the current row."""
        if self.cursor_row is None or self.cursor_row >= len(self.packages):
            return

        pkg = self.packages[self.cursor_row]

        if pkg.id in self.selected_packages:
            self.selected_packages.remove(pkg.id)
            self.update_cell(pkg.id, "checkbox", "☐")
        else:
            self.selected_packages.add(pkg.id)
            self.update_cell(pkg.id, "checkbox", "☑")

    def action_select_all(self) -> None:
        """Select all packages."""
        for pkg in self.packages:
            self.selected_packages.add(pkg.id)
            self.update_cell(pkg.id, "checkbox", "☑")

    def action_deselect_all(self) -> None:
        """Deselect all packages."""
        for pkg in self.packages:
            if pkg.id in self.selected_packages:
                self.selected_packages.remove(pkg.id)
                self.update_cell(pkg.id, "checkbox", "☐")

    def get_selected_packages(self) -> list[Package]:
        """Get list of selected packages.

        Returns:
            List of selected Package objects
        """
        return [pkg for pkg in self.packages if pkg.id in self.selected_packages]


class SearchBox(Container):
    """Search box widget with input and button."""

    class SearchSubmitted(Message):
        """Message sent when search is submitted."""

        def __init__(self, query: str) -> None:
            """Initialize search submitted message.

            Args:
                query: The search query string
            """
            super().__init__()
            self.query = query

    def compose(self) -> ComposeResult:
        """Compose the search box widgets."""
        yield Label("Search:")
        yield Input(placeholder="Enter package name...", id="search_input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission.

        Args:
            event: Input submission event
        """
        self.post_message(self.SearchSubmitted(event.value))


class StatusBar(Static):
    """Status bar showing operation status and counts."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the status bar."""
        super().__init__(*args, **kwargs)
        self.status_text = "Ready"
        self.count = 0

    def on_mount(self) -> None:
        """Set up the status bar when mounted."""
        self.update_status("Ready", 0)

    def update_status(self, status: str, count: int = 0) -> None:
        """Update the status bar.

        Args:
            status: Status message to display
            count: Count to display (e.g., number of packages)
        """
        self.status_text = status
        self.count = count

        if count > 0:
            self.update(f"{status} | {count} packages")
        else:
            self.update(status)

    def set_loading(self, message: str = "Loading...") -> None:
        """Set status to loading state.

        Args:
            message: Loading message to display
        """
        self.update(f"⏳ {message}")

    def set_ready(self, count: int = 0) -> None:
        """Set status to ready state.

        Args:
            count: Number of packages
        """
        self.update_status("Ready", count)

    def set_error(self, message: str) -> None:
        """Set status to error state.

        Args:
            message: Error message to display
        """
        self.update(f"❌ {message}")

    def set_success(self, message: str) -> None:
        """Set status to success state.

        Args:
            message: Success message to display
        """
        self.update(f"✓ {message}")
