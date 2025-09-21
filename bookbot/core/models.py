"""Core data models for BookBot."""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class AudioFormat(str, Enum):
    """Supported audio formats."""
    MP3 = "mp3"
    M4A = "m4a"
    M4B = "m4b"
    FLAC = "flac"
    OGG = "ogg"
    OPUS = "opus"
    AAC = "aac"
    WAV = "wav"


class TrackStatus(str, Enum):
    """Status of a track during processing."""
    PENDING = "pending"
    VALID = "valid"
    MISSING_NUMBER = "missing_number"
    DUPLICATE = "duplicate"
    SUSPICIOUS_DURATION = "suspicious_duration"
    MIXED_FORMAT = "mixed_format"
    ERROR = "error"


class MatchConfidence(str, Enum):
    """Confidence levels for metadata matching."""
    HIGH = "high"        # >0.85 - auto-select
    MEDIUM = "medium"    # 0.65-0.85 - needs confirmation
    LOW = "low"         # <0.65 - manual pick required


class AudioTags(BaseModel):
    """Audio file metadata tags."""
    title: Optional[str] = None
    album: Optional[str] = None
    artist: Optional[str] = None
    albumartist: Optional[str] = None
    track: Optional[int] = None
    disc: Optional[int] = None
    date: Optional[str] = None
    genre: Optional[str] = None
    language: Optional[str] = None
    series: Optional[str] = None
    series_index: Optional[str] = None
    narrator: Optional[str] = None
    comment: Optional[str] = None
    isbn: Optional[str] = None
    asin: Optional[str] = None

    # Raw tag dict for preservation
    raw_tags: Dict[str, Any] = Field(default_factory=dict)


class Track(BaseModel):
    """Represents a single audio track/file."""
    src_path: Path
    disc: int = 1
    track_index: int
    duration: Optional[float] = None  # seconds
    bitrate: Optional[int] = None     # kbps
    channels: Optional[int] = None
    sample_rate: Optional[int] = None
    file_size: int = 0                # bytes
    audio_format: AudioFormat
    existing_tags: AudioTags = Field(default_factory=AudioTags)
    proposed_name: Optional[str] = None
    proposed_tags: Optional[AudioTags] = None
    status: TrackStatus = TrackStatus.PENDING
    warnings: List[str] = Field(default_factory=list)

    @validator('src_path', pre=True)
    def validate_path(cls, v: Union[str, Path]) -> Path:
        return Path(v) if isinstance(v, str) else v

    @property
    def filename(self) -> str:
        """Get the filename without path."""
        return self.src_path.name

    @property
    def stem(self) -> str:
        """Get the filename without extension."""
        return self.src_path.stem

    def get_content_hash(self) -> str:
        """Generate a hash of the file content for integrity checking."""
        hasher = hashlib.sha256()
        with open(self.src_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()


class ProviderIdentity(BaseModel):
    """Canonical identity from a metadata provider."""
    provider: str
    external_id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    series_name: Optional[str] = None
    series_index: Optional[str] = None
    year: Optional[int] = None
    language: Optional[str] = None
    narrator: Optional[str] = None
    edition: Optional[str] = None
    publisher: Optional[str] = None
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    asin: Optional[str] = None
    description: Optional[str] = None
    cover_urls: List[str] = Field(default_factory=list)

    # Raw provider data for reference
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class MatchCandidate(BaseModel):
    """A potential match from a metadata provider."""
    identity: ProviderIdentity
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_level: MatchConfidence
    match_reasons: List[str] = Field(default_factory=list)

    @validator('confidence_level', pre=True, always=True)
    def set_confidence_level(cls, v: Optional[MatchConfidence], values: Dict[str, Any]) -> MatchConfidence:
        if v is not None:
            return v

        confidence = values.get('confidence', 0.0)
        if confidence > 0.85:
            return MatchConfidence.HIGH
        elif confidence >= 0.65:
            return MatchConfidence.MEDIUM
        else:
            return MatchConfidence.LOW


class AudiobookSet(BaseModel):
    """Represents one logical audiobook with its tracks."""
    source_path: Path
    raw_title_guess: Optional[str] = None
    author_guess: Optional[str] = None
    series_guess: Optional[str] = None
    volume_guess: Optional[str] = None
    narrator_guess: Optional[str] = None
    language_guess: Optional[str] = None

    disc_count: int = 1
    total_tracks: int = 0
    total_duration: Optional[float] = None

    tracks: List[Track] = Field(default_factory=list)
    provider_candidates: List[MatchCandidate] = Field(default_factory=list)
    chosen_identity: Optional[ProviderIdentity] = None

    # Validation warnings
    warnings: List[str] = Field(default_factory=list)

    @validator('source_path', pre=True)
    def validate_path(cls, v: Union[str, Path]) -> Path:
        return Path(v) if isinstance(v, str) else v

    @property
    def has_multi_disc(self) -> bool:
        """Check if this set has multiple discs."""
        return self.disc_count > 1

    @property
    def track_count_by_disc(self) -> Dict[int, int]:
        """Get track count per disc."""
        counts: Dict[int, int] = {}
        for track in self.tracks:
            counts[track.disc] = counts.get(track.disc, 0) + 1
        return counts

    def get_tracks_for_disc(self, disc: int) -> List[Track]:
        """Get all tracks for a specific disc, sorted by track index."""
        disc_tracks = [t for t in self.tracks if t.disc == disc]
        return sorted(disc_tracks, key=lambda t: t.track_index)

    def validate_track_order(self) -> List[str]:
        """Validate track ordering and return any issues."""
        issues = []

        for disc in range(1, self.disc_count + 1):
            disc_tracks = self.get_tracks_for_disc(disc)
            if not disc_tracks:
                issues.append(f"Disc {disc} has no tracks")
                continue

            # Check for gaps in track numbering
            track_numbers = sorted([t.track_index for t in disc_tracks])
            expected = list(range(1, len(track_numbers) + 1))
            if track_numbers != expected:
                issues.append(f"Disc {disc} has gaps in track numbering: {track_numbers}")

            # Check for duplicates
            if len(track_numbers) != len(set(track_numbers)):
                duplicates = [n for n in track_numbers if track_numbers.count(n) > 1]
                issues.append(f"Disc {disc} has duplicate track numbers: {duplicates}")

        return issues


class OperationRecord(BaseModel):
    """Record of a file operation for undo functionality."""
    operation_id: str
    timestamp: datetime
    operation_type: str  # 'rename', 'retag', 'convert'

    # File operations
    old_path: Optional[Path] = None
    new_path: Optional[Path] = None
    old_tags: Optional[AudioTags] = None
    new_tags: Optional[AudioTags] = None

    # Integrity checks
    old_content_hash: Optional[str] = None
    new_content_hash: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('old_path', 'new_path', pre=True)
    def validate_paths(cls, v: Optional[Union[str, Path]]) -> Optional[Path]:
        return Path(v) if isinstance(v, str) else v


class RenameOperation(BaseModel):
    """A single rename operation in a transaction."""
    old_path: Path
    new_path: Path
    temp_path: Optional[Path] = None
    track: Track

    @validator('old_path', 'new_path', 'temp_path', pre=True)
    def validate_paths(cls, v: Optional[Union[str, Path]]) -> Optional[Path]:
        return Path(v) if isinstance(v, str) else v


class RenamePlan(BaseModel):
    """Complete plan for renaming operations."""
    plan_id: str
    created_at: datetime
    source_path: Path
    operations: List[RenameOperation] = Field(default_factory=list)
    audiobook_sets: List[AudiobookSet] = Field(default_factory=list)
    dry_run: bool = True

    # Plan validation
    conflicts: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @validator('source_path', pre=True)
    def validate_path(cls, v: Union[str, Path]) -> Path:
        return Path(v) if isinstance(v, str) else v

    def validate_plan(self) -> bool:
        """Validate the rename plan for conflicts and issues."""
        self.conflicts.clear()
        self.warnings.clear()

        # Check for path conflicts
        new_paths = [op.new_path for op in self.operations]
        if len(new_paths) != len(set(new_paths)):
            duplicates = [p for p in new_paths if new_paths.count(p) > 1]
            self.conflicts.extend([f"Duplicate target path: {p}" for p in set(duplicates)])

        # Check for case-insensitive conflicts on case-insensitive filesystems
        if Path.cwd().resolve().as_posix().startswith(('/System', '/Applications')):  # macOS
            lower_paths = [p.as_posix().lower() for p in new_paths]
            if len(lower_paths) != len(set(lower_paths)):
                self.warnings.append("Potential case-insensitive path conflicts detected")

        return len(self.conflicts) == 0