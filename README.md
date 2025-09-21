📚 BookBot: The Audiophile's Audiobook Organizer
Organize your audiobook library with confidence. BookBot is a sleek, powerful, and safety-first TUI (Terminal User Interface) for renaming, organizing, and converting your audiobook collection. Built for audiobook lovers who crave order, it combines smart metadata matching with a bulletproof file operation system.

✨ Badges & Status
<p align="center">
<a href="https://github.com/itsbryanman/BookBot/actions"><img src="https://img.shields.io/github/actions/workflow/status/itsbryanman/BookBot/ci.yml?style=for-the-badge&logo=githubactions&logoColor=white" alt="Build Status"></a>
<a href="https://pypi.org/project/bookbot/"><img src="https://img.shields.io/pypi/v/bookbot?style=for-the-badge&logo=pypi&logoColor=white&color=blue" alt="PyPI Version"></a>
<a href="https://pypi.org/project/bookbot/"><img src="https://img.shields.io/pypi/pyversions/bookbot?style=for-the-badge&logo=python&logoColor=white" alt="Python Versions"></a>
<a href="https://github.com/itsbryanman/BookBot/blob/main/LICENSE"><img src="https://img.shields.io/github/license/itsbryanman/BookBot?style=for-the-badge&color=brightgreen" alt="License: MIT"></a>
<br>
<a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge&logo=python&logoColor=white" alt="Code Style: Black"></a>
<a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=for-the-badge" alt="Linter: Ruff"></a>
<a href="http://mypy-lang.org/"><img src="https://img.shields.io/badge/typed-mypy-blue.svg?style=for-the-badge&logo=python&logoColor=white" alt="Type Checking: Mypy"></a>
<a href="https://github.com/itsbryanman/BookBot/"><img src="https://img.shields.io/github/stars/itsbryanman/BookBot?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Stars"></a>
</p>

🤔 Why BookBot?
Messy audiobook folders are a thing of the past. BookBot was built to solve the most common frustrations with digital audiobook collections, focusing on four core principles:

🛡️ Safety First: Your files are precious. BookBot uses a preview-first workflow, atomic file operations, and full undo capabilities for every transaction. No more accidental deletions or botched renames.

🧠 Intelligent Matching: Leveraging the vast Open Library database, BookBot intelligently scans your files and folder names to find accurate metadata, from authors and series to publication years and cover art.

🎨 Ultimate Flexibility: Your library, your rules. With a powerful templating engine and configurable profiles (e.g., for Plex), you can shape your folder and file structures exactly how you want them.

🚀 Power-Packed Features: Go beyond renaming. BookBot offers an optional, robust pipeline to convert your track-based audiobooks into single, beautifully tagged M4B files, complete with chapter markers and embedded artwork.

🔥 Features
✅ Safe & Reversible Operations: A "dry-run" by default workflow means you preview every change. All file operations are atomic (all-or-nothing) and logged, allowing you to undo any transaction with a simple command.

🤖 Smart Metadata Matching: Integrates seamlessly with Open Library to fetch accurate book information, using fuzzy string matching for impressive accuracy.

✍️ Flexible Naming Templates: Fully customizable filename and folder structures using a simple token system (e.g., {AuthorLastFirst}/{Title} ({Year})).

💽 Multi-Disc & Complex Collection Support: Intelligently parses disc numbers from folder or file names to correctly handle even the most complex audiobook sets.

🎧 M4B Conversion Pipeline: An optional feature to merge audiobook tracks into a single M4B file, powered by FFmpeg. Features include:

Smart encoding (stream-copying AAC tracks, transcoding others).

Automatic chapter marker generation from track boundaries.

Complete metadata tagging, including cover art.

Optional EBU R128 loudness normalization for a consistent listening experience.

🖥️ Cross-Platform TUI: A clean, modern, and intuitive terminal interface built with Textual that works flawlessly on Windows, macOS, and Linux.

⚙️ Configuration Profiles: Switch between pre-configured setups for different use cases like safe (rename only), full (rename & tag), and plex (optimized for Plex Media Server).

🚀 Quick Start
1. Installation (Recommended)
The easiest way to install BookBot is with pipx, which installs it in an isolated environment.

Bash

pipx install bookbot
(See Alternative Installation Methods below for more options.)

2. Launch the TUI
Point BookBot to your audiobooks folder to launch the interactive TUI.

Bash

bookbot tui /path/to/your/audiobooks
3. The TUI Workflow
The TUI will guide you through a simple, 4-step process:

Scan: BookBot analyzes your folder structure and reads existing metadata.

Match: It fetches metadata candidates from Open Library for you to review.

Preview: You see a full list of all proposed file and folder changes before anything is touched.

Apply: Once you confirm, BookBot executes the rename operations safely and atomically.

🛠️ Usage & Commands
Main Commands
bookbot scan <folder>: Scan a directory and print a summary of found audiobooks.

bookbot tui <folder...>: Launch the interactive TUI for one or more folders.

bookbot convert <in> -o <out>: Convert audiobooks to single M4B files.

bookbot undo <transaction-id>: Revert a previously applied operation.

Configuration & Utilities
bookbot config list: List available configuration profiles.

bookbot config show [profile]: Show the configuration for the current or a specific profile.

bookbot history: Show a log of recent transactions.

bookbot --help: Show detailed help for all commands and options.

⚙️ Configuration & Templates
BookBot is powerful out-of-the-box but highly customizable via TOML configuration files.

Profiles
Profiles are an easy way to switch between different settings. For example, to run in Plex-optimized mode:

Bash

bookbot tui --profile plex /path/to/audiobooks
Naming Templates
Customize file and folder names using a rich set of tokens in your config file or directly on the command line.

Example Template:
Folder: {AuthorLastFirst}/{SeriesName|/{SeriesIndex} - }{Title} ({Year})
File: {DiscPad|}{TrackPad} - {Title}

Available Tokens:
{Author}, {AuthorLastFirst}, {Title}, {ShortTitle}, {SeriesName}, {SeriesIndex}, {Year}, {Language}, {Narrator}, {DiscPad}, {TrackPad}, {Disc}, {Track}, {TrackTitle}, {ISBN}.

🤝 Contributing
BookBot is an open-source project, and contributions are highly welcome!

Development Setup
Fork & Clone the repository:

Bash

git clone https://github.com/your-username/BookBot.git
cd BookBot
Install in editable mode with dev dependencies:

Bash

pip install -e ".[dev]"
Run the test suite to ensure everything is working:

Bash

pytest
Run pre-commit checks before submitting a PR:
This will format, lint, and type-check your code.

Bash

make pre-commit
❤️ Credits & Acknowledgements
BookBot stands on the shoulders of giants. A huge thank you to the developers of these incredible open-source libraries:

Textual: For the amazing TUI framework.

Open Library: For providing the book metadata.

Mutagen: For robust audio metadata handling.

FFmpeg: For the powerful audio conversion capabilities.

Click: For the clean command-line interface.

Pydantic: For rock-solid data modeling.

📜 License
This project is licensed under the MIT License. See the LICENSE file for details.

BookBot: Organize your audiobook library with confidence.
