#!/usr/bin/env python3
"""
Package Manager TUI - Modern terminal interface for managing packages.

Built with Textual framework for async operations and rich UI.
"""

import argparse
import asyncio
import sys

from package_manager import WingetManager
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Label, Static, TabbedContent, TabPane
from updater import Updater
from widgets import PackageTable, SearchBox, StatusBar

VERSION = "1.0.0"


class PackageManagerTUI(App):
    """Main TUI application for package management."""

    CSS = """
    Screen {
        background: $surface;
    }

    #search_box {
        height: 3;
        padding: 1;
        background: $panel;
        border: solid $primary;
    }

    #search_input {
        width: 100%;
    }

    PackageTable {
        height: 1fr;
        margin: 1 0;
    }

    .button_bar {
        height: 3;
        padding: 0 1;
        background: $panel;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    StatusBar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }

    .info_panel {
        height: auto;
        padding: 1;
        background: $panel;
        border: solid $accent;
        margin: 1;
    }

    .settings_container {
        padding: 2;
    }

    .setting_row {
        height: 3;
        margin: 1 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+r", "refresh", "Refresh"),
    ]

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the application."""
        super().__init__(*args, **kwargs)
        self.winget = WingetManager()
        self.discover_table: PackageTable | None = None
        self.updates_table: PackageTable | None = None
        self.installed_table: PackageTable | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        with TabbedContent():
            with TabPane("Discover", id="discover_tab"):
                yield from self.compose_discover()
            with TabPane("Updates", id="updates_tab"):
                yield from self.compose_updates()
            with TabPane("Installed", id="installed_tab"):
                yield from self.compose_installed()
            with TabPane("Settings", id="settings_tab"):
                yield from self.compose_settings()
        yield Footer()

    def compose_discover(self) -> ComposeResult:
        """Compose the Discover tab."""
        with Vertical():
            yield SearchBox(id="search_box")
            self.discover_table = PackageTable(show_updates=False, id="discover_table")
            yield self.discover_table
            with Horizontal(classes="button_bar"):
                yield Button("Install Selected", id="install_button", variant="primary")
            yield StatusBar(id="discover_status")

    def compose_updates(self) -> ComposeResult:
        """Compose the Updates tab."""
        with Vertical():
            yield Static(
                "Packages with available updates. Use Space to select, Ctrl+A to select all.",
                classes="info_panel",
            )
            self.updates_table = PackageTable(show_updates=True, id="updates_table")
            yield self.updates_table
            with Horizontal(classes="button_bar"):
                yield Button("Update Selected", id="update_selected_button", variant="primary")
                yield Button("Update All", id="update_all_button", variant="success")
                yield Button("Scan for Updates", id="scan_updates_button", variant="default")
            yield StatusBar(id="updates_status")

    def compose_installed(self) -> ComposeResult:
        """Compose the Installed tab."""
        with Vertical():
            yield Static(
                "Installed packages. Use Space to select packages for removal.",
                classes="info_panel",
            )
            self.installed_table = PackageTable(show_updates=False, id="installed_table")
            yield self.installed_table
            with Horizontal(classes="button_bar"):
                yield Button("Uninstall Selected", id="uninstall_button", variant="error")
                yield Button("Refresh List", id="refresh_installed_button", variant="default")
            yield StatusBar(id="installed_status")

    def compose_settings(self) -> ComposeResult:
        """Compose the Settings tab."""
        with VerticalScroll(classes="settings_container"):
            yield Label("Package Manager TUI Settings", classes="setting_row")
            yield Static(
                f"Version: {VERSION}\n"
                "Package Sources: winget\n"
                "Author: Jesse Slaton\n\n"
                "Keyboard Shortcuts:\n"
                "  Space - Toggle package selection\n"
                "  Ctrl+A - Select all packages\n"
                "  Ctrl+D - Deselect all packages\n"
                "  Ctrl+R - Refresh current tab\n"
                "  Q - Quit application\n\n"
                "Command Line Options:\n"
                "  -U, --update - Check for and install updates\n"
                "  -v, --version - Show version information",
                classes="info_panel",
            )

    async def on_mount(self) -> None:
        """Handle application mount - load initial data."""
        # Load updates on startup
        await self.load_updates()

    async def on_search_box_search_submitted(self, message: SearchBox.SearchSubmitted) -> None:
        """Handle search submission.

        Args:
            message: Search submitted message containing the query
        """
        if not message.query:
            return

        status_bar = self.query_one("#discover_status", StatusBar)
        status_bar.set_loading(f"Searching for '{message.query}'...")

        try:
            packages = await self.winget.search(message.query)
            if self.discover_table:
                self.discover_table.load_packages(packages)
                status_bar.set_ready(len(packages))
        except Exception as e:
            status_bar.set_error(f"Search failed: {e!s}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button pressed event
        """
        button_id = event.button.id

        if button_id == "install_button":
            await self.install_selected()
        elif button_id == "update_selected_button":
            await self.update_selected()
        elif button_id == "update_all_button":
            await self.update_all()
        elif button_id == "scan_updates_button":
            await self.load_updates()
        elif button_id == "uninstall_button":
            await self.uninstall_selected()
        elif button_id == "refresh_installed_button":
            await self.load_installed()

    async def install_selected(self) -> None:
        """Install selected packages from discover tab."""
        if not self.discover_table:
            return

        selected = self.discover_table.get_selected_packages()
        if not selected:
            return

        status_bar = self.query_one("#discover_status", StatusBar)
        status_bar.set_loading(f"Installing {len(selected)} package(s)...")

        success_count = 0
        for pkg in selected:
            if await self.winget.install(pkg.id):
                success_count += 1

        if success_count == len(selected):
            status_bar.set_success(f"Successfully installed {success_count} package(s)")
        else:
            status_bar.set_error(
                f"Installed {success_count}/{len(selected)} package(s), some failed"
            )

    async def update_selected(self) -> None:
        """Update selected packages from updates tab."""
        if not self.updates_table:
            return

        selected = self.updates_table.get_selected_packages()
        if not selected:
            return

        status_bar = self.query_one("#updates_status", StatusBar)
        status_bar.set_loading(f"Updating {len(selected)} package(s)...")

        success_count = 0
        for pkg in selected:
            if await self.winget.upgrade(pkg.id):
                success_count += 1

        if success_count == len(selected):
            status_bar.set_success(f"Successfully updated {success_count} package(s)")
        else:
            status_bar.set_error(
                f"Updated {success_count}/{len(selected)} package(s), some failed"
            )

        # Reload updates after upgrading
        await self.load_updates()

    async def update_all(self) -> None:
        """Update all packages with available updates."""
        if not self.updates_table:
            return

        all_packages = self.updates_table.packages
        if not all_packages:
            return

        status_bar = self.query_one("#updates_status", StatusBar)
        status_bar.set_loading(f"Updating all {len(all_packages)} package(s)...")

        success_count = 0
        for pkg in all_packages:
            if await self.winget.upgrade(pkg.id):
                success_count += 1

        if success_count == len(all_packages):
            status_bar.set_success(f"Successfully updated all {success_count} package(s)")
        else:
            status_bar.set_error(
                f"Updated {success_count}/{len(all_packages)} package(s), some failed"
            )

        # Reload updates after upgrading
        await self.load_updates()

    async def uninstall_selected(self) -> None:
        """Uninstall selected packages from installed tab."""
        if not self.installed_table:
            return

        selected = self.installed_table.get_selected_packages()
        if not selected:
            return

        status_bar = self.query_one("#installed_status", StatusBar)
        status_bar.set_loading(f"Uninstalling {len(selected)} package(s)...")

        success_count = 0
        for pkg in selected:
            if await self.winget.uninstall(pkg.id):
                success_count += 1

        if success_count == len(selected):
            status_bar.set_success(f"Successfully uninstalled {success_count} package(s)")
        else:
            status_bar.set_error(
                f"Uninstalled {success_count}/{len(selected)} package(s), some failed"
            )

        # Reload installed list
        await self.load_installed()

    async def load_updates(self) -> None:
        """Load packages with available updates."""
        if not self.updates_table:
            return

        status_bar = self.query_one("#updates_status", StatusBar)
        status_bar.set_loading("Scanning for updates...")

        try:
            packages = await self.winget.get_updates()
            self.updates_table.load_packages(packages)
            status_bar.set_ready(len(packages))
        except Exception as e:
            status_bar.set_error(f"Failed to load updates: {e!s}")

    async def load_installed(self) -> None:
        """Load installed packages."""
        if not self.installed_table:
            return

        status_bar = self.query_one("#installed_status", StatusBar)
        status_bar.set_loading("Loading installed packages...")

        try:
            packages = await self.winget.get_installed()
            self.installed_table.load_packages(packages)
            status_bar.set_ready(len(packages))
        except Exception as e:
            status_bar.set_error(f"Failed to load installed packages: {e!s}")

    async def action_refresh(self) -> None:
        """Refresh the current tab."""
        # Get the active tab
        tabbed_content = self.query_one(TabbedContent)
        active_tab = tabbed_content.active

        if active_tab == "updates_tab":
            await self.load_updates()
        elif active_tab == "installed_tab":
            await self.load_installed()


def main() -> None:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Package Manager TUI - Modern terminal interface for managing packages"
    )
    parser.add_argument(
        "-U", "--update", action="store_true", help="Check for and install updates"
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"Package Manager TUI v{VERSION}"
    )

    args = parser.parse_args()

    if args.update:
        # Run updater
        asyncio.run(Updater.perform_update())
        sys.exit(0)

    # Run the TUI application
    app = PackageManagerTUI()
    app.run()


if __name__ == "__main__":
    main()
