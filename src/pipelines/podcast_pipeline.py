#!/usr/bin/env python3
"""
Podcast Pipeline: End-to-end automation for converting text to podcast audio.

Usage:
    python3 podcast_pipeline.py --input <file> --title "<title>" [options]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union

from src.clients.openrouter_client import OpenRouterClient
from src.utils.content_segmenter import ContentSegmenter
from src.utils.script_formatter import ScriptFormatter


class PodcastPipeline:
    """Orchestrates the full podcast generation pipeline."""

    def __init__(
        self,
        input_file: Path,
        title: str,
        narrator_name: str = "Narrator",
        voice_path: Optional[Path] = None,
        num_episodes: Union[int, str] = "auto",
        output_dir: Path = Path("resources/sources"),
        short_audio: bool = False,
        openrouter_model: str = "anthropic/claude-3.5-sonnet",
        prompts_path: str = "templates/prompts.yaml"
    ):
        """
        Initialize podcast pipeline.

        Args:
            input_file: Path to input text file
            title: Title of the work
            narrator_name: Name of narrator for config files
            voice_path: Path to voice sample for Chatterbox (optional)
            num_episodes: Number of episodes or "auto"
            output_dir: Base directory for episode sources
            short_audio: Generate short test audio instead of full
            openrouter_model: Model to use for segmentation/formatting
            prompts_path: Path to prompt templates
        """
        self.input_file = input_file
        self.title = title
        self.narrator_name = narrator_name
        self.voice_path = voice_path
        self.num_episodes = num_episodes
        self.output_dir = output_dir
        self.short_audio = short_audio
        self.prompts_path = prompts_path

        # Initialize OpenRouter client and processors
        self.client = OpenRouterClient(model=openrouter_model)
        self.segmenter = ContentSegmenter(self.client, prompts_path)
        self.formatter = ScriptFormatter(self.client, prompts_path)

        # State tracking
        self.episodes = []
        self.episode_dirs = []

    def run(self):
        """Execute the full pipeline."""
        print("=" * 80)
        print("PODCAST PIPELINE")
        print("=" * 80)
        print(f"Input: {self.input_file}")
        print(f"Title: {self.title}")
        print(f"Episodes: {self.num_episodes}")
        print(f"Narrator: {self.narrator_name}")
        print(f"Voice: {self.voice_path or 'Default'}")
        print(f"Mode: {'Short test audio' if self.short_audio else 'Full audio'}")
        print("=" * 80)
        print()

        try:
            # Stage 1: Load content
            print("Stage 1: Loading content...")
            content = self._load_content()
            print(f"Loaded {len(content)} characters")
            print()

            # Stage 2: Segment into episodes
            print("Stage 2: Segmenting into episodes...")
            self.episodes = self.segmenter.segment_content(
                content=content,
                title=self.title,
                num_episodes=self.num_episodes
            )
            print(f"Created {len(self.episodes)} episodes")
            print()

            # Stage 3: Format each episode as script
            print("Stage 3: Formatting scripts...")
            for i, episode in enumerate(self.episodes):
                script = self.formatter.format_episode(
                    episode_content=episode['content'],
                    episode_title=episode['title'],
                    episode_number=episode['episode_number']
                )
                episode['script'] = script

            print(f"Formatted {len(self.episodes)} scripts")
            print()

            # Stage 4: Create source directories
            print("Stage 4: Creating source directories...")
            self._create_source_directories()
            print(f"Created {len(self.episode_dirs)} directories")
            print()

            # Stage 5: Generate audio
            print("Stage 5: Generating audio...")
            self._generate_audio()
            print("Audio generation complete")
            print()

            # Summary
            print("=" * 80)
            print("PIPELINE COMPLETE")
            print("=" * 80)
            print(f"Episodes created: {len(self.episodes)}")
            print(f"Source directories: {self.output_dir}")
            print()
            for i, ep_dir in enumerate(self.episode_dirs, 1):
                print(f"  Episode {i}: {ep_dir}")
            print()
            print("Audio files generated in: audio_output/")
            print("=" * 80)

        except Exception as e:
            print(f"ERROR: Pipeline failed: {str(e)}")
            sys.exit(1)

    def _load_content(self) -> str:
        """Load content from input file."""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            return f.read()

    def _create_source_directories(self):
        """Create source directories with config and script files."""
        # Create sanitized base name from title
        base_name = self.title.lower()
        base_name = base_name.replace(' ', '-')
        base_name = ''.join(c for c in base_name if c.isalnum() or c == '-')

        for episode in self.episodes:
            ep_num = episode['episode_number']

            # Create directory name
            dir_name = f"{base_name}-ep{ep_num}-chatterbox"
            ep_dir = self.output_dir / dir_name
            ep_dir.mkdir(parents=True, exist_ok=True)

            # Create config.json
            config = {
                "id": dir_name,
                "topic": f"{self.title}: Episode {ep_num} - {episode['title']}",
                "narrator": {
                    "name": self.narrator_name
                }
            }

            config_path = ep_dir / "config.json"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            # Create script.txt
            script_path = ep_dir / "script.txt"
            with open(script_path, 'w') as f:
                f.write(episode['script'])

            self.episode_dirs.append(ep_dir)

            print(f"  Created: {ep_dir}")

    def _generate_audio(self):
        """Generate audio for all episodes."""
        for ep_dir in self.episode_dirs:
            print(f"Generating audio for: {ep_dir.name}")

            # Build command
            cmd = [
                "python3",
                "scripts/generate_podcast_audio.py",
                "--source", str(ep_dir),
                "--audio", "chatterbox",
                "--narration"
            ]

            # Add voice if specified
            if self.voice_path:
                cmd.extend(["--audio-prompt-path", str(self.voice_path)])

            # Add short flag if specified
            if self.short_audio:
                cmd.append("--short")

            # Run command
            print(f"  Command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"  ERROR: Audio generation failed for {ep_dir.name}")
                print(f"  STDOUT: {result.stdout}")
                print(f"  STDERR: {result.stderr}")
                raise Exception(f"Audio generation failed for {ep_dir.name}")

            print(f"  ✓ Complete")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Podcast Pipeline: Convert text to podcast audio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-segment and generate test audio
  python3 podcast_pipeline.py --input ~/Downloads/1984.txt --title "1984" --short

  # Specify number of episodes and voice
  python3 podcast_pipeline.py --input book.txt --title "My Book" \\
    --episodes 10 --voice resources/voices/celeste-bedtime.mp3

  # Full audio generation
  python3 podcast_pipeline.py --input book.txt --title "My Book"
        """
    )

    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Input text file'
    )

    parser.add_argument(
        '--title',
        type=str,
        required=True,
        help='Title of the work'
    )

    parser.add_argument(
        '--narrator',
        type=str,
        default='Narrator',
        help='Narrator name (default: Narrator)'
    )

    parser.add_argument(
        '--voice',
        type=Path,
        help='Path to voice sample for Chatterbox'
    )

    parser.add_argument(
        '--episodes',
        default='auto',
        help='Number of episodes or "auto" (default: auto)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('resources/sources'),
        help='Output directory for episode sources (default: resources/sources)'
    )

    parser.add_argument(
        '--short',
        action='store_true',
        help='Generate short test audio instead of full audio'
    )

    parser.add_argument(
        '--model',
        default='anthropic/claude-3.5-sonnet',
        help='OpenRouter model to use (default: claude-3.5-sonnet)'
    )

    parser.add_argument(
        '--prompts',
        type=str,
        default='templates/prompts.yaml',
        help='Path to prompt templates (default: templates/prompts.yaml)'
    )

    args = parser.parse_args()

    # Validate input file
    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)

    # Validate voice file if specified
    if args.voice and not args.voice.exists():
        print(f"ERROR: Voice file not found: {args.voice}")
        sys.exit(1)

    # Parse episodes argument
    if args.episodes != 'auto':
        try:
            num_episodes = int(args.episodes)
        except ValueError:
            print(f"ERROR: --episodes must be a number or 'auto'")
            sys.exit(1)
    else:
        num_episodes = 'auto'

    # Create and run pipeline
    pipeline = PodcastPipeline(
        input_file=args.input,
        title=args.title,
        narrator_name=args.narrator,
        voice_path=args.voice,
        num_episodes=num_episodes,
        output_dir=args.output_dir,
        short_audio=args.short,
        openrouter_model=args.model,
        prompts_path=args.prompts
    )

    pipeline.run()


if __name__ == "__main__":
    main()
