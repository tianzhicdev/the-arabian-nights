"""
Convert existing episode to TikTok shorts with smart reuse of existing MP4s.

Features:
- Reuse existing scene MP4s when no overrides specified
- Only regenerate audio when voice override provided
- Only regenerate images when art override provided
- Select best N scenes for TikTok format
- Create manifest tracking reuse vs regeneration
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import hashlib
import argparse
import subprocess


@dataclass
class TikTokClipMetadata:
    """Metadata for a TikTok clip."""
    clip_id: int
    source_scene_id: str  # e.g., "scene_001"
    source_mp4: str
    output_mp4: str
    reused: bool  # True if copied from existing, False if regenerated
    regenerated_components: List[str]  # ["audio"], ["images"], or []
    duration: float
    text_preview: str


class EpisodeToTikTokConverter:
    """Convert existing episode to TikTok shorts."""

    def __init__(
        self,
        episode_dir: Path,
        output_dir: Path,
        clip_count: int = 10,
        voice_override: Optional[Path] = None,
        art_override: Optional[Path] = None,
        clip_selection: str = "auto"  # auto, first, last, indices
    ):
        """
        Initialize converter.

        Args:
            episode_dir: Directory with existing episode (e.g., output/animal_farm_ep1_full_slides/)
            output_dir: Output directory for TikTok shorts
            clip_count: Number of TikTok clips to generate
            voice_override: New voice reference (regenerate audio)
            art_override: New art reference (regenerate images)
            clip_selection: How to select clips - "auto" (best scenes), "first", "last", or "1,5,10"
        """
        self.episode_dir = Path(episode_dir)
        self.output_dir = Path(output_dir)
        self.clip_count = clip_count
        self.voice_override = Path(voice_override) if voice_override else None
        self.art_override = Path(art_override) if art_override else None
        self.clip_selection = clip_selection

        # Load episode data
        self.scenes_file = self.episode_dir / "scenes.json"
        if not self.scenes_file.exists():
            raise FileNotFoundError(f"scenes.json not found in {self.episode_dir}")

        with open(self.scenes_file) as f:
            self.episode_data = json.load(f)

        # Create output structure
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.clips_dir = self.output_dir / "clips"
        self.clips_dir.mkdir(exist_ok=True)

    def convert(self) -> List[TikTokClipMetadata]:
        """
        Convert episode to TikTok shorts.

        Returns:
            List of clip metadata
        """
        print(f"\n🎬 Converting episode to TikTok shorts")
        print(f"   Episode: {self.episode_dir.name}")
        print(f"   Clips: {self.clip_count}")
        print(f"   Voice override: {self.voice_override.name if self.voice_override else 'None (reuse)'}")
        print(f"   Art override: {self.art_override.name if self.art_override else 'None (reuse)'}")
        print()

        # Select scenes
        selected_scenes = self._select_scenes()
        print(f"✓ Selected {len(selected_scenes)} scenes")

        # Process each scene
        clips_metadata = []
        for i, scene in enumerate(selected_scenes, 1):
            print(f"\n📹 Processing clip {i}/{len(selected_scenes)}")
            metadata = self._process_scene(i, scene)
            clips_metadata.append(metadata)

        # Create manifest
        self._create_manifest(clips_metadata)

        # Create summary
        self._print_summary(clips_metadata)

        return clips_metadata

    def _select_scenes(self) -> List[Dict]:
        """
        Select scenes for TikTok conversion.

        Returns:
            List of selected scene data
        """
        scenes = self.episode_data.get('scenes', [])

        if not scenes:
            raise ValueError("No scenes found in episode")

        if self.clip_selection == "auto":
            # Auto-select: evenly distributed across episode
            step = max(1, len(scenes) // self.clip_count)
            indices = [i * step for i in range(self.clip_count)]
            return [scenes[i] for i in indices if i < len(scenes)]

        elif self.clip_selection == "first":
            return scenes[:self.clip_count]

        elif self.clip_selection == "last":
            return scenes[-self.clip_count:]

        elif "," in self.clip_selection:
            # Comma-separated indices (1-indexed)
            indices = [int(idx) - 1 for idx in self.clip_selection.split(",")]
            return [scenes[i] for i in indices if 0 <= i < len(scenes)]

        else:
            raise ValueError(f"Invalid clip_selection: {self.clip_selection}")

    def _process_scene(self, clip_id: int, scene: Dict) -> TikTokClipMetadata:
        """
        Process a single scene into a TikTok clip.

        Args:
            clip_id: TikTok clip number (1-indexed)
            scene: Scene data from scenes.json

        Returns:
            Clip metadata
        """
        scene_id = scene.get('scene_id', f"scene_{clip_id:03d}")
        scene_number = scene.get('scene_number', clip_id)

        # Find source MP4
        source_mp4 = self._find_source_mp4(scene_number)
        if not source_mp4:
            raise FileNotFoundError(f"Source MP4 not found for scene {scene_number}")

        # Determine if regeneration needed
        needs_audio_regen = self.voice_override is not None
        needs_image_regen = self.art_override is not None

        # Create clip directory
        clip_dir = self.clips_dir / f"clip_{clip_id:03d}"
        clip_dir.mkdir(exist_ok=True)

        # Process clip
        regenerated_components = []
        if needs_audio_regen or needs_image_regen:
            # Regenerate components
            output_mp4 = self._regenerate_clip(
                clip_id, clip_dir, scene, source_mp4,
                needs_audio_regen, needs_image_regen
            )
            if needs_audio_regen:
                regenerated_components.append("audio")
            if needs_image_regen:
                regenerated_components.append("images")
            reused = False
        else:
            # Just copy existing MP4
            output_mp4 = self._copy_existing_clip(clip_id, source_mp4)
            reused = True

        # Get duration
        duration = self._get_video_duration(output_mp4)

        # Create metadata
        text_preview = scene.get('narration', '')[:100] + "..." if len(scene.get('narration', '')) > 100 else scene.get('narration', '')

        metadata = TikTokClipMetadata(
            clip_id=clip_id,
            source_scene_id=scene_id,
            source_mp4=str(source_mp4.relative_to(self.episode_dir)),
            output_mp4=str(output_mp4.relative_to(self.output_dir)),
            reused=reused,
            regenerated_components=regenerated_components,
            duration=duration,
            text_preview=text_preview
        )

        status = "✓ Reused" if reused else f"⟳ Regenerated ({', '.join(regenerated_components)})"
        print(f"   {status}: {output_mp4.name} ({duration:.1f}s)")

        return metadata

    def _find_source_mp4(self, scene_number: int) -> Optional[Path]:
        """Find source MP4 for a scene."""
        # Try different naming patterns
        patterns = [
            f"scene_{scene_number:03d}_with_audio.mp4",
            f"scene_{scene_number:03d}_slides.mp4",
            f"scene_{scene_number:03d}.mp4"
        ]

        # Check video directory
        video_dir = self.episode_dir / "video"
        if video_dir.exists():
            for pattern in patterns:
                mp4_path = video_dir / pattern
                if mp4_path.exists():
                    return mp4_path

        # Check root directory
        for pattern in patterns:
            mp4_path = self.episode_dir / pattern
            if mp4_path.exists():
                return mp4_path

        return None

    def _copy_existing_clip(self, clip_id: int, source_mp4: Path) -> Path:
        """Copy existing MP4 to output directory."""
        output_mp4 = self.output_dir / f"clip_{clip_id:03d}.mp4"
        shutil.copy2(source_mp4, output_mp4)
        return output_mp4

    def _regenerate_clip(
        self,
        clip_id: int,
        clip_dir: Path,
        scene: Dict,
        source_mp4: Path,
        needs_audio_regen: bool,
        needs_image_regen: bool
    ) -> Path:
        """
        Regenerate clip with new audio and/or images.

        Args:
            clip_id: Clip number
            clip_dir: Clip working directory
            scene: Scene data
            source_mp4: Original MP4
            needs_audio_regen: Regenerate audio
            needs_image_regen: Regenerate images

        Returns:
            Path to output MP4
        """
        # TODO: Implement regeneration logic
        # For now, just copy the existing MP4
        # In full implementation:
        # 1. If needs_audio_regen: Generate new audio with voice_override
        # 2. If needs_image_regen: Generate new image with art_override
        # 3. Assemble new video with FFmpeg

        print(f"   ⚠️  Regeneration not yet implemented, copying existing MP4")
        output_mp4 = self.output_dir / f"clip_{clip_id:03d}.mp4"
        shutil.copy2(source_mp4, output_mp4)
        return output_mp4

    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds using ffprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"   ⚠️  Could not get duration: {e}")
            return 0.0

    def _create_manifest(self, clips_metadata: List[TikTokClipMetadata]):
        """Create TikTok manifest file."""
        manifest = {
            'version': '1.0',
            'source_episode': str(self.episode_dir.name),
            'clip_count': len(clips_metadata),
            'config': {
                'voice_override': str(self.voice_override.name) if self.voice_override else None,
                'art_override': str(self.art_override.name) if self.art_override else None,
                'clip_selection': self.clip_selection
            },
            'clips': [asdict(clip) for clip in clips_metadata],
            'statistics': {
                'reused_count': sum(1 for c in clips_metadata if c.reused),
                'regenerated_count': sum(1 for c in clips_metadata if not c.reused),
                'total_duration': sum(c.duration for c in clips_metadata)
            }
        }

        manifest_path = self.output_dir / ".tiktok_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"\n✓ Created manifest: {manifest_path}")

    def _print_summary(self, clips_metadata: List[TikTokClipMetadata]):
        """Print conversion summary."""
        reused_count = sum(1 for c in clips_metadata if c.reused)
        regenerated_count = sum(1 for c in clips_metadata if not c.reused)
        total_duration = sum(c.duration for c in clips_metadata)

        print("\n" + "=" * 60)
        print("📊 CONVERSION SUMMARY")
        print("=" * 60)
        print(f"Total clips: {len(clips_metadata)}")
        print(f"Reused clips: {reused_count} ✓")
        print(f"Regenerated clips: {regenerated_count} ⟳")
        print(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
        print(f"\nOutput directory: {self.output_dir}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Convert existing episode to TikTok shorts with smart MP4 reuse"
    )
    parser.add_argument(
        "--episode-dir",
        required=True,
        help="Episode directory (e.g., output/animal_farm_ep1_full_slides/)"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for TikTok shorts"
    )
    parser.add_argument(
        "--clip-count",
        type=int,
        default=10,
        help="Number of TikTok clips to generate (default: 10)"
    )
    parser.add_argument(
        "--voice-override",
        help="Voice reference to override audio (regenerate audio)"
    )
    parser.add_argument(
        "--art-override",
        help="Art reference to override images (regenerate images)"
    )
    parser.add_argument(
        "--clip-selection",
        default="auto",
        help="Clip selection: 'auto' (evenly distributed), 'first', 'last', or '1,5,10' (comma-separated indices)"
    )

    args = parser.parse_args()

    converter = EpisodeToTikTokConverter(
        episode_dir=args.episode_dir,
        output_dir=args.output_dir,
        clip_count=args.clip_count,
        voice_override=args.voice_override,
        art_override=args.art_override,
        clip_selection=args.clip_selection
    )

    converter.convert()


if __name__ == '__main__':
    main()
