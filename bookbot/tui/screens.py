"""TUI screens for BookBot."""

from pathlib import Path
from typing import List, Optional

from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Label, Static
from textual.widget import Widget

from ..config.manager import ConfigManager
from ..core.models import AudiobookSet
from ..providers.base import MetadataProvider


class SourceSelectionScreen(Static):
    """Screen for selecting source directories."""

    def __init__(self, config_manager: ConfigManager, source_folders: List[Path], **kwargs):
        super().__init__(**kwargs)
        self.config_manager = config_manager
        self.source_folders = source_folders

    def compose(self):
        yield Label("Source Folders:", classes="section-title")

        if self.source_folders:
            for folder in self.source_folders:
                yield Label(f"📁 {folder}")
        else:
            yield Label("No folders selected")

        yield Button("Add Folder", id="add_folder")


class ScanResultsScreen(Static):
    """Screen showing scan results."""

    def __init__(self, config_manager: ConfigManager, **kwargs):
        super().__init__(**kwargs)
        self.config_manager = config_manager
        self.audiobook_sets: List[AudiobookSet] = []

    def compose(self):
        yield Label("Scan Results", classes="section-title")
        yield DataTable(id="scan_results_table")

    def set_audiobook_sets(self, audiobook_sets: List[AudiobookSet]):
        """Set the audiobook sets to display."""
        self.audiobook_sets = audiobook_sets

        table = self.query_one("#scan_results_table", DataTable)
        table.clear(columns=True)

        # Add columns
        table.add_columns("Folder", "Tracks", "Discs", "Title Guess", "Warnings")

        # Add rows
        for audiobook_set in audiobook_sets:
            warnings = f"{len(audiobook_set.warnings)} warning(s)" if audiobook_set.warnings else "None"
            table.add_row(
                audiobook_set.source_path.name,
                str(audiobook_set.total_tracks),
                str(audiobook_set.disc_count),
                audiobook_set.raw_title_guess or "Unknown",
                warnings
            )


class MatchReviewScreen(Static):
    """Screen for reviewing metadata matches."""

    def __init__(self, config_manager: ConfigManager, provider: MetadataProvider, **kwargs):
        super().__init__(**kwargs)
        self.config_manager = config_manager
        self.provider = provider
        self.audiobook_sets: List[AudiobookSet] = []

    def compose(self):
        yield Label("Metadata Matches", classes="section-title")
        yield DataTable(id="matches_table")

    async def find_matches(self, audiobook_sets: List[AudiobookSet]):
        """Find matches for audiobook sets."""
        self.audiobook_sets = audiobook_sets

        table = self.query_one("#matches_table", DataTable)
        table.clear(columns=True)
        table.add_columns("Audiobook", "Best Match", "Confidence", "Action")

        for audiobook_set in audiobook_sets:
            # Find matches using the provider
            candidates = await self.provider.find_matches(audiobook_set)

            if candidates:
                best_match = candidates[0]
                audiobook_set.provider_candidates = candidates
                audiobook_set.chosen_identity = best_match.identity

                table.add_row(
                    audiobook_set.raw_title_guess or "Unknown",
                    f"{best_match.identity.title} - {', '.join(best_match.identity.authors)}",
                    f"{best_match.confidence:.2f}",
                    "✓ Accept" if best_match.confidence > 0.85 else "⚠ Review"
                )
            else:
                table.add_row(
                    audiobook_set.raw_title_guess or "Unknown",
                    "No matches found",
                    "0.00",
                    "❌ Manual"
                )


class PreviewScreen(Static):
    """Screen for previewing changes."""

    def __init__(self, config_manager: ConfigManager, **kwargs):
        super().__init__(**kwargs)
        self.config_manager = config_manager
        self.audiobook_sets: List[AudiobookSet] = []

    def compose(self):
        yield Label("Preview Changes", classes="section-title")
        yield DataTable(id="preview_table")

    def set_audiobook_sets(self, audiobook_sets: List[AudiobookSet]):
        """Set audiobook sets and generate preview."""
        self.audiobook_sets = audiobook_sets

        table = self.query_one("#preview_table", DataTable)
        table.clear(columns=True)
        table.add_columns("Current Name", "Proposed Name", "Status")

        from ..core.templates import TemplateEngine
        template_engine = TemplateEngine()

        for audiobook_set in audiobook_sets:
            for track in audiobook_set.tracks:
                current_name = track.src_path.name

                if audiobook_set.chosen_identity:
                    proposed_name = template_engine.generate_filename(
                        track, audiobook_set, audiobook_set.chosen_identity
                    )
                else:
                    proposed_name = current_name

                status = "✓ Ready" if proposed_name != current_name else "→ No change"
                table.add_row(current_name, proposed_name, status)

    async def apply_changes(self) -> bool:
        """Apply the previewed changes."""
        # TODO: Implement actual file operations
        return True


class ConversionScreen(Static):
    """Screen for M4B conversion options."""

    def __init__(self, config_manager: ConfigManager, **kwargs):
        super().__init__(**kwargs)
        self.config_manager = config_manager

    def compose(self):
        yield Label("M4B Conversion", classes="section-title")
        yield Label("Conversion options will be available here")
        yield Button("Start Conversion", id="start_conversion", disabled=True)