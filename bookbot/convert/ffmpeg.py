"""FFmpeg wrapper for audio conversion operations."""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.models import AudioFormat, Track


class FFmpegWrapper:
    """Wrapper for FFmpeg operations."""

    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()

    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable."""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return 'ffmpeg'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        raise RuntimeError("FFmpeg not found. Please install FFmpeg.")

    def _find_ffprobe(self) -> str:
        """Find FFprobe executable."""
        try:
            result = subprocess.run(['ffprobe', '-version'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return 'ffprobe'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        raise RuntimeError("FFprobe not found. Please install FFmpeg.")

    def probe_file(self, file_path: Path) -> Dict:
        """Get detailed information about an audio file."""
        cmd = [
            self.ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(file_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"FFprobe failed: {result.stderr}")

            return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to probe file {file_path}: {e}")

    def get_duration(self, file_path: Path) -> float:
        """Get duration of an audio file in seconds."""
        probe_data = self.probe_file(file_path)

        # Try to get duration from format first, then from streams
        if 'format' in probe_data and 'duration' in probe_data['format']:
            return float(probe_data['format']['duration'])

        for stream in probe_data.get('streams', []):
            if stream.get('codec_type') == 'audio' and 'duration' in stream:
                return float(stream['duration'])

        raise RuntimeError(f"Could not determine duration for {file_path}")

    def analyze_loudness(self, file_path: Path) -> Dict[str, float]:
        """Analyze loudness using EBU R128."""
        cmd = [
            self.ffmpeg_path,
            '-i', str(file_path),
            '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json',
            '-f', 'null',
            '-'
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            # FFmpeg outputs the JSON to stderr for this filter
            stderr_lines = result.stderr.strip().split('\n')
            json_started = False
            json_lines = []

            for line in stderr_lines:
                if line.strip() == '{':
                    json_started = True

                if json_started:
                    json_lines.append(line)

                if line.strip() == '}' and json_started:
                    break

            if json_lines:
                json_text = '\n'.join(json_lines)
                loudness_data = json.loads(json_text)
                return {
                    'input_i': float(loudness_data.get('input_i', 0)),
                    'input_tp': float(loudness_data.get('input_tp', 0)),
                    'input_lra': float(loudness_data.get('input_lra', 0)),
                    'target_offset': float(loudness_data.get('target_offset', 0))
                }

            raise RuntimeError("No loudness data found in FFmpeg output")

        except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Failed to analyze loudness for {file_path}: {e}")

    def convert_to_aac(self, input_path: Path, output_path: Path,
                      bitrate: Optional[str] = None, vbr_quality: Optional[int] = None,
                      normalize: bool = False, target_lufs: float = -16.0) -> bool:
        """Convert audio file to AAC format."""
        cmd = [self.ffmpeg_path, '-i', str(input_path)]

        # Audio filters
        filters = []

        if normalize:
            filters.append(f'loudnorm=I={target_lufs}:TP=-1.5:LRA=11')

        if filters:
            cmd.extend(['-af', ','.join(filters)])

        # Audio codec and quality settings
        cmd.extend(['-c:a', 'aac'])

        if vbr_quality is not None:
            # Use VBR encoding
            cmd.extend(['-q:a', str(vbr_quality)])
        elif bitrate:
            # Use CBR encoding
            cmd.extend(['-b:a', bitrate])
        else:
            # Default to 128k CBR
            cmd.extend(['-b:a', '128k'])

        # Ensure proper AAC profile
        cmd.extend(['-profile:a', 'aac_low'])

        # Output file
        cmd.extend(['-y', str(output_path)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def concatenate_files(self, input_files: List[Path], output_path: Path,
                         chapters: Optional[List[Dict]] = None) -> bool:
        """Concatenate multiple audio files into one."""
        # Create a temporary file list for FFmpeg concat
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = Path(f.name)
            for file_path in input_files:
                # Escape single quotes in filenames
                escaped_path = str(file_path).replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        try:
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                '-y', str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            success = result.returncode == 0

            # Add chapters if provided
            if success and chapters:
                success = self.add_chapters(output_path, chapters)

            return success

        except subprocess.TimeoutExpired:
            return False
        finally:
            # Clean up temporary file
            try:
                concat_file.unlink()
            except FileNotFoundError:
                pass

    def add_chapters(self, file_path: Path, chapters: List[Dict]) -> bool:
        """Add chapter markers to an audio file."""
        # Create chapters metadata file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            chapters_file = Path(f.name)

            f.write(";FFMETADATA1\n")

            for i, chapter in enumerate(chapters):
                start_time = int(chapter['start'] * 1000)  # Convert to milliseconds
                end_time = int(chapter['end'] * 1000)
                title = chapter.get('title', f'Chapter {i + 1}')

                f.write(f"\n[CHAPTER]\n")
                f.write(f"TIMEBASE=1/1000\n")
                f.write(f"START={start_time}\n")
                f.write(f"END={end_time}\n")
                f.write(f"title={title}\n")

        try:
            # Create a temporary output file
            temp_output = file_path.with_suffix('.tmp.m4b')

            cmd = [
                self.ffmpeg_path,
                '-i', str(file_path),
                '-i', str(chapters_file),
                '-map_metadata', '1',
                '-c', 'copy',
                '-y', str(temp_output)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                # Replace original with chaptered version
                file_path.unlink()
                temp_output.rename(file_path)
                return True
            else:
                # Clean up temp file on failure
                if temp_output.exists():
                    temp_output.unlink()
                return False

        except subprocess.TimeoutExpired:
            return False
        finally:
            # Clean up chapters file
            try:
                chapters_file.unlink()
            except FileNotFoundError:
                pass

    def embed_cover_art(self, file_path: Path, cover_path: Path) -> bool:
        """Embed cover art into an audio file."""
        # Create a temporary output file
        temp_output = file_path.with_suffix('.tmp.m4b')

        cmd = [
            self.ffmpeg_path,
            '-i', str(file_path),
            '-i', str(cover_path),
            '-map', '0',
            '-map', '1',
            '-c', 'copy',
            '-c:v:1', 'mjpeg',
            '-disposition:v:0', 'attached_pic',
            '-y', str(temp_output)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                # Replace original with version that has cover art
                file_path.unlink()
                temp_output.rename(file_path)
                return True
            else:
                # Clean up temp file on failure
                if temp_output.exists():
                    temp_output.unlink()
                return False

        except subprocess.TimeoutExpired:
            return False

    def can_stream_copy(self, file_path: Path) -> bool:
        """Check if a file can be stream copied (already AAC)."""
        try:
            probe_data = self.probe_file(file_path)

            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    codec = stream.get('codec_name', '').lower()
                    return codec == 'aac'

            return False
        except Exception:
            return False

    def set_metadata(self, file_path: Path, metadata: Dict[str, str]) -> bool:
        """Set metadata tags on an audio file."""
        temp_output = file_path.with_suffix('.tmp.m4b')

        cmd = [self.ffmpeg_path, '-i', str(file_path)]

        # Add metadata options
        for key, value in metadata.items():
            if value:  # Only add non-empty values
                cmd.extend(['-metadata', f'{key}={value}'])

        cmd.extend(['-c', 'copy', '-y', str(temp_output)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                file_path.unlink()
                temp_output.rename(file_path)
                return True
            else:
                if temp_output.exists():
                    temp_output.unlink()
                return False

        except subprocess.TimeoutExpired:
            return False