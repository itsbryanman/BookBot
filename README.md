# BookBot

A cross-platform TUI audiobook renamer and organizer with a safety-first approach and optional M4B conversion.

## Features

- **Safe Rename Operations**: Preview-first workflow with atomic commits and full undo capability
- **Smart Metadata Matching**: Integrates with Open Library for accurate book information
- **Flexible Naming Templates**: Customizable filename and folder structures
- **Multi-Disc Support**: Handles complex audiobook collections correctly
- **M4B Conversion**: Optional pipeline to merge tracks into single M4B files with chapters
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **TUI Interface**: Clean terminal interface built with Textual
- **Configuration Profiles**: Pre-configured setups for different use cases

## Installation

### Using pipx (Recommended)

```bash
pipx install bookbot
```

### Using pip

```bash
pip install bookbot
```

### From Source

```bash
git clone https://github.com/itsbryanman/BookBot.git
cd BookBot
pip install -e .
```

## Quick Start

### Basic Usage

1. **Scan a directory**:
   ```bash
   bookbot scan /path/to/audiobooks
   ```

2. **Launch interactive TUI**:
   ```bash
   bookbot tui /path/to/audiobooks
   ```

3. **Convert to M4B** (requires FFmpeg):
   ```bash
   bookbot convert /path/to/audiobooks -o /path/to/output
   ```

### TUI Workflow

1. **Scan**: Discover audiobook files and analyze structure
2. **Match**: Find metadata from Open Library
3. **Preview**: Review proposed changes before applying
4. **Apply**: Execute rename operations safely
5. **Convert**: Optionally merge to M4B format

## Configuration

BookBot uses profiles for different use cases:

- **safe**: Rename only, no tagging (default)
- **full**: Complete processing with tags and artwork
- **plex**: Optimized for Plex Media Server
- **conversion**: Enables M4B conversion

### Switch Profiles

```bash
bookbot config list
bookbot tui --profile plex /path/to/audiobooks
```

### Naming Templates

Customize how files are named using template tokens:

```
{AuthorLastFirst}/{SeriesName}/{SeriesIndex} - {Title} ({Year})
{DiscPad}{TrackPad} - {Title}
```

Available tokens:
- `{Author}`, `{AuthorLastFirst}` - Author name variations
- `{Title}`, `{ShortTitle}` - Book title variations
- `{SeriesName}`, `{SeriesIndex}` - Series information
- `{Year}`, `{Language}`, `{Narrator}` - Publication details
- `{DiscPad}`, `{TrackPad}` - Zero-padded disc/track numbers
- `{ISBN}` - Book identifier

## M4B Conversion

Convert multi-track audiobooks to single M4B files:

```bash
# Basic conversion
bookbot convert /audiobooks -o /m4b-output

# With custom settings
bookbot convert /audiobooks -o /output \\
  --bitrate 128k \\
  --normalize \\
  --chapters auto
```

### Requirements for Conversion

- FFmpeg must be installed and available in PATH
- Enable conversion in profile or config

### Conversion Features

- **Smart encoding**: Stream-copy AAC, transcode others
- **Chapter markers**: Generated from track boundaries
- **Metadata**: Complete tagging with cover art
- **Audio normalization**: Optional EBU R128 loudness normalization

## Commands

### Main Commands

- `bookbot scan <folder>` - Scan directory for audiobooks
- `bookbot tui <folder>...` - Launch interactive interface
- `bookbot convert <folder> -o <output>` - Convert to M4B
- `bookbot undo <transaction-id>` - Undo previous operation

### Configuration

- `bookbot config list` - List available profiles
- `bookbot config show [profile]` - Show configuration details
- `bookbot config reset` - Reset to defaults

### Utilities

- `bookbot history` - Show recent operations
- `bookbot --help` - Show detailed help

## File Organization

BookBot works with common audiobook directory structures:

```
Author Name/
├── Book 1 - Title/
│   ├── CD1/
│   │   ├── 01 - Chapter 1.mp3
│   │   └── 02 - Chapter 2.mp3
│   └── CD2/
│       └── 01 - Chapter 3.mp3
└── Book 2 - Another Title/
    └── Single File.m4b
```

### Supported Formats

**Input**: MP3, M4A, M4B, FLAC, OGG, Opus, AAC, WAV
**Output**: Original format preserved, or M4B for conversion

## Safety Features

- **Dry-run by default**: No changes without explicit confirmation
- **Atomic operations**: All-or-nothing file operations
- **Conflict detection**: Prevents overwrites and naming collisions
- **Undo capability**: Reverse operations with transaction logs
- **Backup preservation**: Original tags and paths recorded

## Advanced Usage

### Custom Templates

Create custom naming templates in config:

```toml
[templates.my_template]
name = "My Custom Template"
folder_template = "{Author}/{Title}"
file_template = "{TrackPad} {Title}"
```

### Batch Processing

Process multiple directories:

```bash
bookbot tui /audiobooks/fantasy /audiobooks/scifi /audiobooks/mystery
```

### Filtering and Selection

Use command-line options for automated processing:

```bash
# Scan with specific settings
bookbot scan /audiobooks \\
  --profile safe \\
  --template plex \\
  --lang en \\
  --no-tag
```

## Troubleshooting

### Common Issues

1. **No audiobooks found**: Check file extensions and directory structure
2. **FFmpeg not found**: Install FFmpeg for conversion features
3. **Permission errors**: Ensure write access to target directories
4. **Metadata matching fails**: Check internet connection for API access

### Getting Help

- Use `bookbot --help` for command details
- Check logs in `~/.local/share/bookbot/logs/`
- Review configuration with `bookbot config show`

### Debug Mode

Enable verbose logging:

```bash
export BOOKBOT_DEBUG=1
bookbot tui /audiobooks
```

## Contributing

BookBot is open source and welcomes contributions:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Setup

```bash
git clone https://github.com/itsbryanman/BookBot.git
cd BookBot
pip install -e ".[dev]"
pytest
```

## License

MIT License - see LICENSE file for details.

## Credits

- Built with [Textual](https://github.com/Textualize/textual) for the TUI
- Metadata from [Open Library](https://openlibrary.org/)
- Audio processing via [Mutagen](https://mutagen.readthedocs.io/)
- Conversion powered by [FFmpeg](https://ffmpeg.org/)

---

*BookBot: Organize your audiobook library with confidence*