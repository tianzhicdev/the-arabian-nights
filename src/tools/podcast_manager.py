#!/usr/bin/env python3
"""
Podcast Manager - Main CLI Orchestrator
Coordinates script generation and audio production for podcasts
"""

import argparse
import sys
from pathlib import Path

from src.utils.config_manager import ConfigManager
from script_generator import ScriptGenerator
from audio_generator import AudioGenerator


class PodcastManager:
    """Main orchestrator for podcast generation"""

    def __init__(self):
        """Initialize PodcastManager"""
        self.config_manager = ConfigManager()
        self.script_generator = ScriptGenerator()
        self.audio_generator = AudioGenerator()

    def generate_podcast(self, podcast_id: str = None, topic: str = None,
                        test_mode: bool = False, test_mp3: bool = False, force: bool = False):
        """
        Generate complete podcast (script + audio)

        Args:
            podcast_id: Podcast ID to generate
            topic: Topic to search for
            test_mode: If True, generate short script (8-10 dialogues) and short audio (first 4 dialogues)
            test_mp3: If True, generate only short audio (first 4 dialogues), keep full script
            force: If True, regenerate even if files exist
        """
        # Load config and find podcast
        self.config_manager.load_config()
        podcast = self.config_manager.get_podcast(podcast_id=podcast_id, topic=topic)

        if not podcast:
            print(f"✗ Podcast not found: {podcast_id or topic}")
            return False

        print(f"\n{'='*60}")
        print(f"PODCAST GENERATION: {podcast['topic']}")
        print(f"{'='*60}")

        # Step 1: Generate script if needed
        # Note: When test_mp3=True, we NEVER regenerate the script (even with --force)
        elevenlabs_ready_exists = self.script_generator.check_script_exists(podcast)

        if test_mp3:
            # test-mp3 mode: always keep existing script
            print("\n✓ TEST-MP3 mode: Using existing script")
            print(f"  ElevenLabs: {podcast['elevenlabs_ready_filepath']}")
        elif elevenlabs_ready_exists and not force:
            print("\n✓ Script already exists, skipping generation")
            print(f"  ElevenLabs: {podcast['elevenlabs_ready_filepath']}")
        else:
            if force:
                print("\n⚠ FORCE mode: Regenerating script...")
            else:
                print("\n→ Script not found, generating...")

            elevenlabs_script = self.script_generator.generate_script(podcast, test_mode=test_mode)
            elevenlabs_filepath = self.script_generator.save_script(
                podcast, elevenlabs_script
            )

            # Update config with file path
            self.config_manager.update_podcast_filepaths(
                podcast['id'],
                elevenlabs_ready_filepath=elevenlabs_filepath
            )
            self.config_manager.save_config()

        # Step 2: Generate audio if needed
        existing_audio = self.audio_generator.check_audio_exists(podcast['id'])

        if existing_audio and not force:
            print("\n✓ Audio already exists, skipping generation")
            print(f"  MP3: {existing_audio}")
        else:
            if force:
                print("\n⚠ FORCE mode: Regenerating audio...")
            else:
                print("\n→ Audio not found, generating...")

            # Use test mode for audio if either test_mode or test_mp3 is True
            audio_test_mode = test_mode or test_mp3
            mp3_filepath = self.audio_generator.generate_audio(podcast, force_regenerate=force, test_mode=audio_test_mode)

            # Update config with MP3 path
            self.config_manager.update_podcast_filepaths(
                podcast['id'],
                mp3_filepath=mp3_filepath
            )
            self.config_manager.save_config()

        # Final status
        print(f"\n{'='*60}")
        print("✓ PODCAST GENERATION COMPLETE")
        print(f"{'='*60}")

        # Reload to get updated data
        self.config_manager.load_config()
        podcast = self.config_manager.get_podcast(podcast_id=podcast['id'])

        print(f"\nFiles generated:")
        print(f"  ElevenLabs: {podcast['elevenlabs_ready_filepath']}")
        print(f"  MP3: {podcast['mp3_filepath']}")

        if podcast['metadata']['file_size_mb']:
            print(f"\nMP3 Info:")
            print(f"  Size: {podcast['metadata']['file_size_mb']} MB")
            print(f"  Generated: {podcast['metadata']['generation_date']}")

        return True

    def list_podcasts(self):
        """List all podcasts in config"""
        self.config_manager.load_config()
        podcasts = self.config_manager.list_podcasts()

        print(f"\n{'='*60}")
        print(f"PODCASTS ({len(podcasts)} total)")
        print(f"{'='*60}\n")

        for i, podcast in enumerate(podcasts, 1):
            print(f"{i}. {podcast['topic']}")
            print(f"   ID: {podcast['id']}")
            print(f"   Hosts: {podcast['host_1']['name']} vs {podcast['host_2']['name']}")

            status = self.config_manager.check_files_exist(podcast['id'])
            print(f"   Status:")
            print(f"     ElevenLabs: {'✓' if status['elevenlabs_ready_exists'] else '✗'}")
            print(f"     MP3: {'✓' if status['mp3_exists'] else '✗'}")
            print()

    def status(self, podcast_id: str):
        """Show detailed status for a podcast"""
        self.config_manager.load_config()
        podcast = self.config_manager.get_podcast(podcast_id=podcast_id)

        if not podcast:
            print(f"✗ Podcast not found: {podcast_id}")
            return

        print(f"\n{'='*60}")
        print(f"PODCAST STATUS: {podcast['topic']}")
        print(f"{'='*60}\n")

        print(f"ID: {podcast['id']}")
        print(f"Topic: {podcast['topic']}")
        print(f"\nHosts:")
        print(f"  Host 1: {podcast['host_1']['name']}")
        print(f"    Voice ID: {podcast['host_1']['voice_id']}")
        print(f"    Notes: {podcast['host_1']['editor_notes']}")
        print(f"  Host 2: {podcast['host_2']['name']}")
        print(f"    Voice ID: {podcast['host_2']['voice_id']}")
        print(f"    Notes: {podcast['host_2']['editor_notes']}")

        print(f"\nTheme: {podcast['editor_notes']}")

        status = self.config_manager.check_files_exist(podcast['id'])
        print(f"\nFiles:")
        print(f"  ElevenLabs: {podcast['elevenlabs_ready_filepath'] or 'Not set'}")
        print(f"    Exists: {'✓' if status['elevenlabs_ready_exists'] else '✗'}")
        print(f"  MP3: {podcast['mp3_filepath'] or 'Not set'}")
        print(f"    Exists: {'✓' if status['mp3_exists'] else '✗'}")

        if podcast['metadata']['file_size_mb']:
            print(f"\nMetadata:")
            print(f"  File Size: {podcast['metadata']['file_size_mb']} MB")
            print(f"  Generated: {podcast['metadata']['generation_date']}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Podcast Generator - Manage and generate podcast scripts and audio"
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate podcast (script + audio)')
    gen_parser.add_argument('--id', help='Podcast ID')
    gen_parser.add_argument('--topic', help='Podcast topic')
    gen_parser.add_argument('--test', action='store_true',
                           help='Test mode: Generate short script (8-10 dialogues) and short audio (first 4 dialogues). Use with --force.')
    gen_parser.add_argument('--test-mp3', action='store_true',
                           help='Test MP3 mode: Generate only short audio (first 4 dialogues), keep full script')
    gen_parser.add_argument('--force', action='store_true',
                           help='Force regeneration even if files exist')

    # List command
    subparsers.add_parser('list', help='List all podcasts')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show podcast status')
    status_parser.add_argument('--id', required=True, help='Podcast ID')

    # Generate all command
    gen_all_parser = subparsers.add_parser('generate-all', help='Generate all podcasts')
    gen_all_parser.add_argument('--test', action='store_true',
                               help='Test mode: Generate only 10 dialogues')
    gen_all_parser.add_argument('--force', action='store_true',
                               help='Force regeneration even if files exist')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = PodcastManager()

    try:
        if args.command == 'generate':
            if not args.id and not args.topic:
                print("Error: Either --id or --topic must be specified")
                sys.exit(1)
            manager.generate_podcast(
                podcast_id=args.id,
                topic=args.topic,
                test_mode=args.test,
                test_mp3=getattr(args, 'test_mp3', False),
                force=args.force
            )

        elif args.command == 'list':
            manager.list_podcasts()

        elif args.command == 'status':
            manager.status(args.id)

        elif args.command == 'generate-all':
            manager.config_manager.load_config()
            podcasts = manager.config_manager.list_podcasts()
            print(f"\nGenerating {len(podcasts)} podcasts...")

            for podcast in podcasts:
                manager.generate_podcast(
                    podcast_id=podcast['id'],
                    test_mode=args.test,
                    force=args.force
                )
                print("\n")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
