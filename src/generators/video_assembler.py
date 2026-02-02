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
        """Concatenate multiple videos with re-encoding for consistency."""
        # Create concat file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = f.name
            for video in video_paths:
                f.write(f"file '{video.absolute()}'\n")

        try:
            # Re-encode to ensure consistent codec/framerate across all clips
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '18',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-ar', '44100',
                '-ac', '2',
                '-movflags', '+faststart',
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
        output_path: Path,
        zoom_per_sec: float = 0.0
    ):
        """
        Create a slide video from an image with audio, optionally with zoom effect.

        Args:
            image_path: Path to image file
            audio_path: Path to audio file
            output_path: Path for output video
            zoom_per_sec: Zoom percentage per second (e.g., 0.02 = 2% per sec). 0 = no zoom.
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
        fps = 25

        if zoom_per_sec > 0:
            # Ken Burns zoom effect using zoompan filter
            # Use 30fps for smoother motion
            fps = 30
            total_frames = int(audio_duration * fps)
            # Zoom formula: start at 1.0, increase by zoom_per_sec each second
            zoom_expr = f"1+{zoom_per_sec}*on/{fps}"

            # Build FFmpeg command with zoompan
            # Scale up source image for better zoom quality, use fps=30 for smoothness
            cmd = [
                'ffmpeg',
                '-loop', '1',
                '-i', str(image_path),
                '-i', str(audio_path),
                '-filter_complex',
                f"[0:v]scale=3840:2160,zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1280x720:fps={fps},format=yuv420p[v]",
                '-map', '[v]',
                '-map', '1:a',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '18',
                '-r', str(fps),
                '-c:a', 'aac',
                '-b:a', '192k',
                '-t', str(audio_duration),
                '-y',
                str(output_path)
            ]
        else:
            # Static image (no zoom)
            cmd = [
                'ffmpeg',
                '-loop', '1',
                '-i', str(image_path),
                '-i', str(audio_path),
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '18',
                '-vf', 'scale=1280:720,format=yuv420p',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-t', str(audio_duration),
                '-shortest',
                '-y',
                str(output_path)
            ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg slide video creation failed: {result.stderr}")

    def create_video_with_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        target_width: int = 1280,
        target_height: int = 720
    ):
        """
        Trim video to audio duration and overlay audio, resize to target dimensions.

        Args:
            video_path: Path to source video
            audio_path: Path to audio file
            output_path: Path for output video
            target_width: Target width
            target_height: Target height
        """
        # Get audio duration
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

        # Trim video to audio duration, resize, and replace audio
        # Ensure consistent encoding: 30fps, yuv420p, libx264, aac
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-i', str(audio_path),
            '-t', str(audio_duration),
            '-vf', f'scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p',
            '-map', '0:v',
            '-map', '1:a',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '18',
            '-r', '30',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '44100',
            '-ac', '2',
            '-shortest',
            '-y',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg video+audio merge failed: {result.stderr}")

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

    def add_branding(
        self,
        main_video_path: Path,
        output_path: Path,
        logo_path: Path,
        intro_sound_path: Path,
        bg_music_path: Path,
        intro_duration: float = 2.0,
        outro_duration: float = 10.0,
        fade_duration: float = 2.0,
        bg_music_volume: float = 0.15,
        target_width: int = 1280,
        target_height: int = 720
    ):
        """
        Add intro/outro branding to a video.

        Args:
            main_video_path: Path to the main content video
            output_path: Path for final branded video
            logo_path: Path to logo image
            intro_sound_path: Path to intro sound effect (e.g., woosh)
            bg_music_path: Path to background music loop
            intro_duration: Intro duration in seconds (default 2s)
            outro_duration: Outro duration in seconds (default 10s)
            fade_duration: Music fade out duration at end (default 2s)
            bg_music_volume: Volume for background music (0.0-1.0, default 0.15)
            target_width: Video width (default 1280)
            target_height: Video height (default 720)
        """
        import tempfile

        # Get main video duration
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(main_video_path)
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        main_duration = float(result.stdout.strip())

        # Create temp directory for intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            intro_video = temp_dir / "intro.mp4"
            main_with_music = temp_dir / "main_with_music.mp4"
            outro_video = temp_dir / "outro.mp4"

            # 1. Create intro video: logo on black with woosh sound
            print("  Creating intro...")
            self._create_logo_video(
                logo_path, intro_sound_path, intro_video,
                duration=intro_duration,
                target_width=target_width, target_height=target_height
            )

            # 2. Add background music to main video (loop music, mix at low volume)
            print("  Adding background music to main content...")
            self._add_background_music(
                main_video_path, bg_music_path, main_with_music,
                music_volume=bg_music_volume
            )

            # 3. Create outro video: logo with music, fade out
            print("  Creating outro...")
            self._create_logo_video_with_fade(
                logo_path, bg_music_path, outro_video,
                duration=outro_duration,
                fade_duration=fade_duration,
                target_width=target_width, target_height=target_height
            )

            # 4. Concatenate all parts
            print("  Concatenating intro + main + outro...")
            self.concatenate_videos(
                [intro_video, main_with_music, outro_video],
                output_path
            )

        total_duration = intro_duration + main_duration + outro_duration
        print(f"  ✓ Branded video: {total_duration:.1f}s total")

    def _create_logo_video(
        self,
        logo_path: Path,
        audio_path: Path,
        output_path: Path,
        duration: float,
        target_width: int = 1280,
        target_height: int = 720
    ):
        """Create a video with logo centered on black background."""
        # Scale logo to fit within frame (max 50% of frame size), center on black
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'color=c=black:s={target_width}x{target_height}:r=30:d={duration}',
            '-i', str(logo_path),
            '-i', str(audio_path),
            '-filter_complex',
            f'[1:v]scale=w=min(iw\\,{target_width}*0.5):h=min(ih\\,{target_height}*0.5):force_original_aspect_ratio=decrease[logo];'
            f'[0:v][logo]overlay=(W-w)/2:(H-h)/2:format=auto[v]',
            '-map', '[v]',
            '-map', '2:a',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-r', '30',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '44100',
            '-ac', '2',
            '-t', str(duration),
            '-y',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to create logo video: {result.stderr}")

    def _create_logo_video_with_fade(
        self,
        logo_path: Path,
        music_path: Path,
        output_path: Path,
        duration: float,
        fade_duration: float = 2.0,
        target_width: int = 1280,
        target_height: int = 720
    ):
        """Create a video with logo and music that fades out at the end."""
        fade_start = duration - fade_duration

        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'color=c=black:s={target_width}x{target_height}:r=30:d={duration}',
            '-i', str(logo_path),
            '-stream_loop', '-1',  # Loop the music
            '-i', str(music_path),
            '-filter_complex',
            f'[1:v]scale=w=min(iw\\,{target_width}*0.5):h=min(ih\\,{target_height}*0.5):force_original_aspect_ratio=decrease[logo];'
            f'[0:v][logo]overlay=(W-w)/2:(H-h)/2:format=auto[v];'
            f'[2:a]afade=t=out:st={fade_start}:d={fade_duration}[a]',
            '-map', '[v]',
            '-map', '[a]',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-r', '30',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '44100',
            '-ac', '2',
            '-t', str(duration),
            '-y',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to create outro video: {result.stderr}")

    def _add_background_music(
        self,
        video_path: Path,
        music_path: Path,
        output_path: Path,
        music_volume: float = 0.15
    ):
        """Add looped background music to video, mixed at low volume."""
        # Get video duration
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        video_duration = float(result.stdout.strip())

        # Mix: keep original audio at full volume, add music at low volume
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-stream_loop', '-1',  # Loop the music
            '-i', str(music_path),
            '-filter_complex',
            f'[1:a]volume={music_volume}[music];'
            f'[0:a][music]amix=inputs=2:duration=first:dropout_transition=0[a]',
            '-map', '0:v',
            '-map', '[a]',
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '44100',
            '-ac', '2',
            '-t', str(video_duration),
            '-y',
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to add background music: {result.stderr}")
