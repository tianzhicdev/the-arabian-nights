#!/usr/bin/env python3
"""
Video Assembly and Post-Processing.
Handles trimming, concatenation, and audio merging.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List


class VideoAssembler:
    """Assemble final video from scenes"""

    def trim_video(self, video_path: Path, target_duration: float, output_path: Path):
        """
        Trim video to exact duration using re-encoding for precision.

        Uses libx264 with fast preset for quick encoding while maintaining quality.
        This ensures frame-accurate trimming instead of keyframe-only cuts.
        """
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-t', str(target_duration),
            '-c:v', 'libx264',      # Re-encode video for precise trimming
            '-preset', 'fast',       # Fast encoding preset
            '-crf', '18',            # High quality (lower = better, 18 is visually lossless)
            '-c:a', 'aac',           # Re-encode audio
            '-b:a', '192k',          # Audio bitrate
            '-avoid_negative_ts', 'make_zero',  # Handle timestamp issues
            '-y',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg trim failed: {result.stderr}")

        # Validate trimmed duration
        self._validate_duration(output_path, target_duration)

    def _validate_duration(self, video_path: Path, expected_duration: float, tolerance: float = 0.05):
        """
        Validate that video duration matches expected duration within tolerance.

        Args:
            video_path: Path to video file
            expected_duration: Expected duration in seconds
            tolerance: Acceptable difference in seconds (default 0.05s = 50ms)
        """
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]

        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffprobe failed: {result.stderr}")

        actual_duration = float(result.stdout.strip())
        diff = abs(actual_duration - expected_duration)

        if diff > tolerance:
            print(f"  ⚠️  Duration mismatch: expected {expected_duration:.3f}s, got {actual_duration:.3f}s (diff: {diff:.3f}s)")
            # Try speed adjustment as fallback (works for both too-long and too-short videos)
            self._speed_adjust_video(video_path, actual_duration, expected_duration)

    def _speed_adjust_video(self, video_path: Path, current_duration: float, target_duration: float):
        """
        Adjust video speed to match target duration.

        This is a fallback method when trimming doesn't achieve exact duration.
        """
        speed_factor = current_duration / target_duration

        # Create temp file
        temp_path = video_path.parent / f"{video_path.stem}_temp{video_path.suffix}"

        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-filter_complex', f'[0:v]setpts={1/speed_factor}*PTS[v];[0:a]atempo={speed_factor}[a]',
            '-map', '[v]',
            '-map', '[a]',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-y',
            str(temp_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ⚠️  Speed adjustment failed: {result.stderr}")
            temp_path.unlink(missing_ok=True)
            return

        # Replace original with speed-adjusted version
        video_path.unlink()
        temp_path.rename(video_path)
        print(f"  ✓ Speed adjusted by {speed_factor:.3f}x to match target duration")

    def concatenate_videos(self, video_paths: List[Path], output_path: Path):
        """Concatenate multiple videos"""
        # Create concat file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = f.name
            for video in video_paths:
                f.write(f"file '{video.absolute()}'\n")

        try:
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                '-y',
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"ffmpeg concat failed: {result.stderr}")
        finally:
            Path(concat_file).unlink(missing_ok=True)

    def add_audio_to_video(self, video_path: Path, audio_path: Path, output_path: Path):
        """Add audio track to video"""
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-i', str(audio_path),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v',
            '-map', '1:a',
            '-shortest',
            '-y',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg audio merge failed: {result.stderr}")

    def create_slide_video(
        self,
        image_path: Path,
        audio_path: Path,
        output_path: Path
    ):
        """
        Create a static slide video from an image with audio (no waveform).

        Just displays the image for the duration of the audio.
        Used for slides mode - cheaper alternative to full video generation.

        Args:
            image_path: Path to image file
            audio_path: Path to audio file
            output_path: Path for output video
        """
        # Get audio duration using ffprobe
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]

        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffprobe failed: {result.stderr}")

        audio_duration = float(result.stdout.strip())

        # Build FFmpeg command - just loop image for audio duration
        cmd = [
            'ffmpeg',
            '-loop', '1',                      # Loop the image
            '-i', str(image_path),             # Input image
            '-i', str(audio_path),             # Audio file
            '-c:v', 'libx264',                 # Video codec
            '-preset', 'fast',                 # Encoding preset
            '-crf', '18',                      # High quality
            '-vf', 'scale=1280:720,format=yuv420p',  # Scale and ensure compatible format
            '-c:a', 'aac',                     # Audio codec
            '-b:a', '192k',                    # Audio bitrate
            '-t', str(audio_duration),         # Duration matches audio
            '-shortest',                       # Stop at shortest stream
            '-y',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg slide video creation failed: {result.stderr}")

    def create_static_video_with_waveform(
        self,
        background_image_path: Path,
        audio_path: Path,
        output_path: Path,
        waveform_style: str = "showwaves"
    ):
        """
        Create video from static background image + audio + waveform overlay.

        Args:
            background_image_path: Path to background image
            audio_path: Path to audio file
            output_path: Path for output video
            waveform_style: FFmpeg waveform filter (showwaves, showspectrum, etc.)
        """
        # Get audio duration using ffprobe
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]

        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffprobe failed: {result.stderr}")

        audio_duration = float(result.stdout.strip())

        # Build FFmpeg command with waveform overlay
        cmd = [
            'ffmpeg',
            '-loop', '1',                      # Loop the image
            '-i', str(background_image_path),  # Background image
            '-i', str(audio_path),             # Audio file
            '-filter_complex',
            f'[0:v]scale=1280:720,format=yuv420p[bg];'  # Scale background and ensure compatible pixel format
            f'[1:a]showwaves=s=1280x200:mode=cline:colors=white@0.7:scale=sqrt[waveform];'  # Generate waveform
            f'[bg][waveform]overlay=(W-w)/2:H-h-50[v]',  # Overlay waveform at bottom center
            '-map', '[v]',                     # Map video output
            '-map', '1:a',                     # Map audio
            '-c:v', 'libx264',                 # Video codec
            '-preset', 'fast',                 # Encoding preset
            '-crf', '18',                      # High quality
            '-c:a', 'aac',                     # Audio codec
            '-b:a', '192k',                    # Audio bitrate
            '-t', str(audio_duration),         # Duration matches audio
            '-y',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg static video creation failed: {result.stderr}")
