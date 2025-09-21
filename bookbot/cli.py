"""Command-line interface for BookBot."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click

from .config.manager import ConfigManager
from .core.discovery import AudioFileScanner
from .core.operations import TransactionManager
from .providers.openlibrary import OpenLibraryProvider


@click.group()
@click.version_option()
@click.option('--config-dir', type=click.Path(path_type=Path),
              help='Configuration directory path')
@click.pass_context
def cli(ctx: click.Context, config_dir: Optional[Path]) -> None:
    """BookBot - A cross-platform TUI audiobook renamer and organizer."""
    # Ensure that ctx.obj exists and is a dict
    ctx.ensure_object(dict)

    # Initialize configuration manager
    ctx.obj['config_manager'] = ConfigManager(config_dir)


@cli.command()
@click.argument('folder', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--dry-run', is_flag=True, default=True,
              help='Show what would be done without making changes')
@click.option('--profile', type=str, help='Configuration profile to use')
@click.option('--recurse', type=int, default=5, help='Maximum recursion depth')
@click.option('--no-tag', is_flag=True, help='Skip tagging operations')
@click.option('--template', type=str, help='Naming template to use')
@click.option('--lang', type=str, default='en', help='Preferred language')
@click.option('--cache', type=click.Path(path_type=Path), help='Cache directory')
@click.option('--log', type=click.Path(path_type=Path), help='Log file path')
@click.pass_context
def scan(ctx: click.Context, folder: Path, dry_run: bool, profile: Optional[str],
         recurse: int, no_tag: bool, template: Optional[str], lang: str,
         cache: Optional[Path], log: Optional[Path]) -> None:
    """Scan a folder for audiobooks and propose renames."""
    config_manager = ctx.obj['config_manager']

    # Apply profile if specified
    if profile:
        if not config_manager.apply_profile(profile):
            click.echo(f"Error: Profile '{profile}' not found", err=True)
            sys.exit(1)

    config = config_manager.load_config()

    # Override config with command line options
    if no_tag:
        config.tagging.enabled = False
    if template:
        config.active_template = template

    # Initialize scanner
    scanner = AudioFileScanner(recursive=True, max_depth=recurse)

    try:
        click.echo(f"Scanning {folder}...")
        audiobook_sets = scanner.scan_directory(folder)

        if not audiobook_sets:
            click.echo("No audiobooks found in the specified directory.")
            return

        click.echo(f"Found {len(audiobook_sets)} audiobook set(s):")

        for i, audiobook_set in enumerate(audiobook_sets, 1):
            click.echo(f"\n{i}. {audiobook_set.source_path.name}")
            click.echo(f"   Tracks: {audiobook_set.total_tracks}")
            click.echo(f"   Discs: {audiobook_set.disc_count}")

            if audiobook_set.raw_title_guess:
                click.echo(f"   Title: {audiobook_set.raw_title_guess}")
            if audiobook_set.author_guess:
                click.echo(f"   Author: {audiobook_set.author_guess}")

            if audiobook_set.warnings:
                click.echo("   Warnings:")
                for warning in audiobook_set.warnings:
                    click.echo(f"     - {warning}")

        if dry_run:
            click.echo("\nDry run completed. Use 'bookbot tui' for interactive processing.")

    except Exception as e:
        click.echo(f"Error scanning directory: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('folders', nargs=-1, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--profile', type=str, help='Configuration profile to use')
@click.pass_context
def tui(ctx: click.Context, folders: tuple[Path, ...], profile: Optional[str]) -> None:
    """Launch the interactive TUI for audiobook processing."""
    config_manager = ctx.obj['config_manager']

    # Apply profile if specified
    if profile:
        if not config_manager.apply_profile(profile):
            click.echo(f"Error: Profile '{profile}' not found", err=True)
            sys.exit(1)

    if not folders:
        click.echo("Error: At least one folder must be specified", err=True)
        sys.exit(1)

    try:
        # Import TUI app here to avoid issues if textual is not installed
        from .tui.app import BookBotApp

        app = BookBotApp(config_manager, list(folders))
        app.run()

    except ImportError:
        click.echo("Error: Textual is required for TUI mode. Install with: pip install textual", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error running TUI: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('folder', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('-o', '--output', type=click.Path(path_type=Path), required=True,
              help='Output directory for converted files')
@click.option('--profile', type=str, help='Configuration profile to use')
@click.option('--bitrate', type=str, default='128k', help='AAC bitrate (e.g., 128k)')
@click.option('--vbr', type=int, help='VBR quality (1-6, overrides bitrate)')
@click.option('--normalize', is_flag=True, help='Normalize audio levels')
@click.option('--chapters', type=click.Choice(['auto', 'from-tags']), default='auto',
              help='Chapter creation method')
@click.option('--no-art', is_flag=True, help='Skip cover art embedding')
@click.option('--dry-run', is_flag=True, help='Show conversion plan without executing')
@click.pass_context
def convert(ctx: click.Context, folder: Path, output: Path, profile: Optional[str],
           bitrate: str, vbr: Optional[int], normalize: bool, chapters: str,
           no_art: bool, dry_run: bool) -> None:
    """Convert audiobooks to M4B format."""
    config_manager = ctx.obj['config_manager']

    # Apply profile if specified
    if profile:
        if not config_manager.apply_profile(profile):
            click.echo(f"Error: Profile '{profile}' not found", err=True)
            sys.exit(1)

    config = config_manager.load_config()

    # Check if conversion is enabled in config
    if not config.conversion.enabled:
        click.echo("Error: M4B conversion is not enabled in configuration", err=True)
        click.echo("Enable it with a conversion profile or modify your config")
        sys.exit(1)

    try:
        # Import conversion module
        from .convert.pipeline import ConversionPipeline

        pipeline = ConversionPipeline(config_manager)

        # Override config with command line options
        conv_config = config.conversion.model_copy()
        conv_config.output_directory = output
        if vbr:
            conv_config.use_vbr = True
            conv_config.vbr_quality = vbr
        else:
            conv_config.bitrate = bitrate
        conv_config.normalize_audio = normalize
        conv_config.chapter_naming = chapters
        conv_config.write_cover_art = not no_art

        click.echo(f"Converting audiobooks from {folder} to {output}...")

        if dry_run:
            # Show conversion plan
            plan = pipeline.create_conversion_plan(folder, conv_config)
            click.echo(f"Conversion plan created with {len(plan.operations)} operation(s)")
            # TODO: Display plan details
        else:
            # Execute conversion
            success = pipeline.convert_directory(folder, conv_config)
            if success:
                click.echo("Conversion completed successfully!")
            else:
                click.echo("Conversion failed!", err=True)
                sys.exit(1)

    except ImportError as e:
        if 'ffmpeg' in str(e).lower():
            click.echo("Error: FFmpeg is required for conversion. Please install FFmpeg.", err=True)
        else:
            click.echo(f"Error: Missing dependency for conversion: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error during conversion: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('transaction_id', type=str)
@click.pass_context
def undo(ctx: click.Context, transaction_id: str) -> None:
    """Undo a previous operation by transaction ID."""
    config_manager = ctx.obj['config_manager']
    transaction_manager = TransactionManager(config_manager)

    try:
        if transaction_manager.undo_transaction(transaction_id):
            click.echo(f"Transaction {transaction_id} undone successfully")
        else:
            click.echo(f"Failed to undo transaction {transaction_id}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error undoing transaction: {e}", err=True)
        sys.exit(1)


@cli.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command('list')
@click.pass_context
def config_list(ctx: click.Context) -> None:
    """List configuration profiles."""
    config_manager = ctx.obj['config_manager']
    profiles = config_manager.list_profiles()

    if not profiles:
        click.echo("No profiles found")
        return

    click.echo("Available profiles:")
    for name, description in profiles.items():
        click.echo(f"  {name}: {description}")


@config.command('show')
@click.argument('profile_name', type=str, required=False)
@click.pass_context
def config_show(ctx: click.Context, profile_name: Optional[str]) -> None:
    """Show configuration details."""
    config_manager = ctx.obj['config_manager']

    if profile_name:
        profile = config_manager.load_profile(profile_name)
        if not profile:
            click.echo(f"Profile '{profile_name}' not found", err=True)
            sys.exit(1)
        config_data = profile.config
        click.echo(f"Profile: {profile.name}")
        click.echo(f"Description: {profile.description}")
    else:
        config_data = config_manager.load_config()
        click.echo("Current configuration:")

    # Display key configuration settings
    click.echo(f"Safe mode: {config_data.safe_mode}")
    click.echo(f"Active template: {config_data.active_template}")
    click.echo(f"Tagging enabled: {config_data.tagging.enabled}")
    click.echo(f"Conversion enabled: {config_data.conversion.enabled}")


@config.command('reset')
@click.confirmation_option(prompt='Reset configuration to defaults?')
@click.pass_context
def config_reset(ctx: click.Context) -> None:
    """Reset configuration to defaults."""
    config_manager = ctx.obj['config_manager']
    config_manager.reset_to_defaults()
    click.echo("Configuration reset to defaults")


@cli.command()
@click.option('--days', type=int, default=30, help='Show transactions from last N days')
@click.pass_context
def history(ctx: click.Context, days: int) -> None:
    """Show operation history."""
    config_manager = ctx.obj['config_manager']
    transaction_manager = TransactionManager(config_manager)

    transactions = transaction_manager.list_transactions(days)

    if not transactions:
        click.echo("No transactions found")
        return

    click.echo(f"Transactions from last {days} days:")
    for transaction in transactions:
        status = transaction.get('status', 'completed')
        undo_info = "" if transaction['can_undo'] else " (cannot undo)"
        click.echo(f"  {transaction['id'][:8]}... - "
                  f"{transaction['timestamp']} - "
                  f"{transaction['operation_count']} operations - "
                  f"{status}{undo_info}")


def main() -> None:
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()