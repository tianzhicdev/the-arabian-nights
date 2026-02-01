#!/usr/bin/env python3
"""
Complete Episode Generator: Research → Script → Audio

Usage:
    python3 scripts/generate_episode.py \
        --host1 "Josef Stalin" \
        --host1-voice "rfkTsdZrVWEVhDycUYn9" \
        --host2 "Mao Zedong" \
        --host2-voice "MzqUf1HbJ8UmQ0wUsx2p" \
        --topic "War Strategy" \
        --notes "Discussion of military tactics" \
        --duration 10m
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from research_agent import PerplexityResearchAgent
from src.utils.prompt_builder import PromptBuilder
from script_generator import ScriptGenerator
from audio_generator import AudioGenerator
from src.utils.config_manager import ConfigManager


class EpisodeGenerator:
    """Complete episode generation pipeline"""

    def __init__(self, model: str = None):
        self.research_agent = PerplexityResearchAgent()
        self.prompt_builder = PromptBuilder()
        self.script_gen = ScriptGenerator(model=model)
        self.audio_gen = AudioGenerator()
        self.config_mgr = ConfigManager()

        self.project_root = Path(__file__).parent.parent

    def generate_episode(self,
                        host1: str,
                        host1_voice: str,
                        host1_notes: str,
                        host2: str,
                        host2_voice: str,
                        host2_notes: str,
                        topic: str,
                        notes: str,
                        duration: str = "15m",
                        enable_research: bool = True,
                        model: str = "anthropic/claude-sonnet-4.5"):
        """
        Complete pipeline: Research → Script → Audio

        Returns:
            Dict with script_path, mp3_path, episode_id
        """
        # Parse duration
        duration_minutes = self.prompt_builder.parse_duration(duration)

        # Generate episode ID
        episode_id = self._generate_id(topic, host1, host2)

        print(f"\n{'=' * 70}")
        print(f"EPISODE GENERATION: {topic}")
        print(f"{'=' * 70}")
        print(f"  Hosts: {host1} vs {host2}")
        print(f"  Duration: {duration_minutes} minutes (~{duration_minutes * 150} words)")
        print(f"  Episode ID: {episode_id}")
        print(f"{'=' * 70}\n")

        # STAGE 1: RESEARCH
        research = None
        if enable_research:
            print("→ Stage 1/3: Research (Perplexity Sonar Pro via OpenRouter)")
            try:
                research = self.research_agent.research_hosts_and_topic(
                    host1, host2, topic
                )
                print("  ✓ Research complete\n")
            except Exception as e:
                print(f"  ✗ Research failed: {e}")
                print("  Continuing without research...\n")
                research = None
        else:
            print("→ Stage 1/3: Research skipped\n")

        # STAGE 2: SCRIPT GENERATION
        print("→ Stage 2/3: Script Generation (Claude Sonnet 4.5 via OpenRouter)")

        # Build system prompt
        system_prompt = self.prompt_builder.build_system_prompt(
            host1=host1,
            host2=host2,
            topic=topic,
            notes=notes,
            duration_minutes=duration_minutes,
            host1_notes=host1_notes,
            host2_notes=host2_notes,
            research=research
        )

        # Generate script using existing script_generator
        print(f"  Generating dialogue with {model}...")
        script = self.script_gen.generate_script_from_prompt(
            system_prompt=system_prompt,
            topic=topic,
            host1_name=host1,
            host2_name=host2,
            duration_minutes=duration_minutes,
            model=model
        )

        print(f"  ✓ Script complete ({len(script.split())} words)")

        # Clean script to remove any JSON metadata or config blocks
        script = self._clean_script(script)
        print(f"  ✓ Cleaned script ({len(script.split())} words)\n")

        # Create output directory
        output_dir = self.project_root / "output" / episode_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save script to output directory
        transcript_path = output_dir / "transcript.txt"
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(script)
        print(f"  ✓ Saved transcript: output/{episode_id}/transcript.txt\n")

        # STAGE 3: AUDIO GENERATION
        print("→ Stage 3/3: Audio Generation (ElevenLabs)")

        # Build temporary config for audio generation
        temp_config = {
            'id': episode_id,
            'topic': topic,
            'host_1': {
                'name': host1,
                'voice_id': host1_voice,
                'editor_notes': host1_notes or f"Historical figure in conversation about {topic}"
            },
            'host_2': {
                'name': host2,
                'voice_id': host2_voice,
                'editor_notes': host2_notes or f"Historical figure in conversation about {topic}"
            },
            'editor_notes': notes or f"A conversation about {topic}",
            'elevenlabs_ready_filepath': str(transcript_path),
            'status': {
                'elevenlabs_ready_exists': True,
                'mp3_exists': False,
                'last_generated': None
            },
            'metadata': {
                'duration_seconds': None,
                'file_size_mb': None,
                'generation_date': None
            }
        }

        try:
            mp3_source_path = self.audio_gen.generate_audio(
                temp_config,
                force_regenerate=True
            )

            # Move MP3 to output directory
            if mp3_source_path:
                import shutil
                mp3_source = self.project_root / mp3_source_path
                mp3_dest = output_dir / "episode.mp3"
                shutil.move(str(mp3_source), str(mp3_dest))

                # Also move speed variations
                audio_dir = self.project_root / "audio_output"
                base_filename = Path(mp3_source_path).stem
                for speed_file in audio_dir.glob(f"{base_filename}_*.mp3"):
                    speed_dest = output_dir / speed_file.name
                    shutil.move(str(speed_file), str(speed_dest))

                print(f"  ✓ Audio saved: output/{episode_id}/episode.mp3\n")
                mp3_path = mp3_dest
            else:
                mp3_path = None

        except Exception as e:
            print(f"  ✗ Audio generation failed: {e}")
            import traceback
            traceback.print_exc()
            mp3_path = None

        # Save config.json with input parameters
        config_data = {
            'episode_id': episode_id,
            'generated_at': datetime.now().isoformat(),
            'input_parameters': {
                'host1': host1,
                'host1_voice': host1_voice,
                'host1_notes': host1_notes,
                'host2': host2,
                'host2_voice': host2_voice,
                'host2_notes': host2_notes,
                'topic': topic,
                'notes': notes,
                'duration': duration,
                'research_enabled': enable_research
            },
            'output_files': {
                'transcript': 'transcript.txt',
                'audio': 'episode.mp3' if mp3_path else None
            }
        }

        config_path = output_dir / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved config: output/{episode_id}/config.json")

        print(f"\n{'=' * 70}")
        print("✓ EPISODE COMPLETE")
        print(f"{'=' * 70}\n")
        print(f"Output directory: output/{episode_id}/")
        print(f"  - transcript.txt")
        print(f"  - config.json")
        if mp3_path:
            print(f"  - episode.mp3")
            # List speed variations
            variations = list(output_dir.glob("*_*x.mp3"))
            if variations:
                print(f"  - {len(variations)} speed variations")
        print()

        return {
            'episode_id': episode_id,
            'output_dir': str(output_dir),
            'transcript_path': str(transcript_path),
            'mp3_path': str(mp3_path) if mp3_path else None
        }

    def _generate_id(self, topic: str, host1: str, host2: str) -> str:
        """Generate kebab-case episode ID"""
        # Clean topic
        topic_clean = topic.lower().replace(' ', '-').replace(':', '').replace(',', '')

        # Get last names
        host1_last = host1.split()[-1].lower()
        host2_last = host2.split()[-1].lower()

        # Combine: topic-host1-vs-host2
        episode_id = f"{topic_clean}-{host1_last}-vs-{host2_last}"

        # Remove any invalid characters
        episode_id = ''.join(c for c in episode_id if c.isalnum() or c == '-')

        return episode_id

    def _clean_script(self, script: str) -> str:
        """
        Remove JSON config blocks, metadata, file headers, and markdown from script.
        Claude sometimes adds these despite instructions to output only dialogue.

        Returns only the actual dialogue portion.
        """
        lines = script.split('\n')
        dialogue_start = None
        in_code_block = False

        # Find where dialogue actually starts
        # Dialogue format: "Name: [tag] text" or "Name: text"
        for i, line in enumerate(lines):
            stripped = line.strip()

            # Track markdown code blocks
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                continue

            # Skip lines inside code blocks
            if in_code_block:
                continue

            # Skip empty lines, comments, file headers
            if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                continue

            # Skip JSON-looking lines
            if stripped.startswith('{') or stripped.startswith('}') or stripped.startswith('"'):
                continue

            # Check if line looks like dialogue: "SpeakerName: ..."
            if ':' in stripped:
                speaker_part = stripped.split(':')[0].strip()
                # Valid speaker name should:
                # 1. Not start with JSON/markdown characters
                # 2. Not be a JSON key
                # 3. Contain letters (actual names)
                if (speaker_part and
                    not any(c in speaker_part for c in ['{', '}', '"', '[', ']', '#']) and
                    not stripped.startswith('"') and
                    any(c.isalpha() for c in speaker_part)):
                    dialogue_start = i
                    break

        # If no dialogue found, return original (fail safe)
        if dialogue_start is None:
            return script

        # Return only dialogue portion
        return '\n'.join(lines[dialogue_start:])


def main():
    parser = argparse.ArgumentParser(
        description="Generate podcast episode with research, script, and audio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # AI-Powered Voice Selection (NEW!)
  python3 scripts/generate_episode.py \\
    --host1 "Jesus" \\
    --host1-notes "warm, laughing, relatable, early 30s, iced coffee energy" \\
    --host2 "Buddha" \\
    --host2-notes "calm, peaceful, quiet wisdom, old wise male" \\
    --topic "Genesis - The OG Drama" \\
    --duration 15m

  # Minimal AI Selection (infers from names)
  python3 scripts/generate_episode.py \\
    --host1 "Margaret Thatcher" \\
    --host2 "Cleopatra" \\
    --topic "Power and Politics" \\
    --duration 10m

  # Partial Override (AI selects host2 only)
  python3 scripts/generate_episode.py \\
    --host1 "Josef Stalin" \\
    --host1-voice "rfkTsdZrVWEVhDycUYn9" \\
    --host2 "Mao Zedong" \\
    --host2-notes "Chinese military strategist, commanding" \\
    --topic "War Strategy" \\
    --duration 10m

  # Full Manual Override (classic mode)
  python3 scripts/generate_episode.py \\
    --host1 "Albert Einstein" \\
    --host1-voice "DfE5EkknFF950NR6OMui" \\
    --host2 "Isaac Newton" \\
    --host2-voice "SF9uvIlY93SJRMdV5jeP" \\
    --topic "Physics" \\
    --no-research

Supported Models:
  OpenRouter (requires OPEN_ROUTER_API in .env.secrets):
    - anthropic/claude-sonnet-4.5 (default, highest quality)
    - anthropic/claude-3.5-haiku (faster, cheaper)
    - openai/gpt-4-turbo
    - openai/gpt-4

  Ollama (requires Ollama running locally - free & unlimited):
    - ollama:dolphin-mistral (7B, fast, uncensored)
    - ollama:nous-hermes2 (8x7B, good quality)
    - ollama:qwen2.5:14b (14B, balanced)
    - ollama:qwen2.5:32b (32B, high quality, slower)
    - ollama:mixtral:8x7b-instruct (47B effective, excellent)

  Ollama Setup:
    1. Install: curl -fsSL https://ollama.ai/install.sh | sh
    2. Pull model: ollama pull dolphin-mistral
    3. Start server: ollama serve (runs in background)
    4. Use with: --model "ollama:dolphin-mistral"

  Note: Ollama models are free but may produce lower quality output
        than Claude. Best for testing or high-volume generation.
        """
    )

    # Required arguments
    parser.add_argument('--host1', required=True, help='Host 1 full name')
    parser.add_argument('--host1-voice', help='Host 1 ElevenLabs voice ID (optional - AI will select if not provided)')
    parser.add_argument('--host1-notes', default='', help='Host 1 character notes (used for AI voice selection)')

    parser.add_argument('--host2', required=True, help='Host 2 full name')
    parser.add_argument('--host2-voice', help='Host 2 ElevenLabs voice ID (optional - AI will select if not provided)')
    parser.add_argument('--host2-notes', default='', help='Host 2 character notes (used for AI voice selection)')

    parser.add_argument('--topic', required=True, help='Episode topic/theme')
    parser.add_argument('--notes', default='', help='Episode notes/discussion points')

    # Optional
    parser.add_argument('--duration', default='15m', help='Target duration (e.g., "10m", "20min")')
    parser.add_argument('--no-research', action='store_true', help='Skip research phase (faster)')
    parser.add_argument('--model', default='anthropic/claude-sonnet-4.5',
                       help='Model for script generation. OpenRouter: "anthropic/claude-sonnet-4.5", "gpt-4". '
                            'Ollama (local): "ollama:dolphin-mistral", "ollama:nous-hermes2". '
                            'See --help for full list.')

    args = parser.parse_args()

    # AI Voice Selection (if voice IDs not provided)
    host1_voice = args.host1_voice
    host2_voice = args.host2_voice

    if not host1_voice or not host2_voice:
        from voice_selector_ai import select_voices_for_episode

        # Build descriptions for AI
        host1_desc = args.host1_notes if args.host1_notes else f"{args.host1} discussing {args.topic}"
        host2_desc = args.host2_notes if args.host2_notes else f"{args.host2} discussing {args.topic}"

        # Select voices with AI
        voice_selection = select_voices_for_episode(
            host1_name=args.host1,
            host1_description=host1_desc,
            host2_name=args.host2,
            host2_description=host2_desc,
            host1_voice_override=host1_voice,
            host2_voice_override=host2_voice
        )

        host1_voice = voice_selection["host1_voice_id"]
        host2_voice = voice_selection["host2_voice_id"]

    generator = EpisodeGenerator(model=args.model)

    try:
        result = generator.generate_episode(
            host1=args.host1,
            host1_voice=host1_voice,
            host1_notes=args.host1_notes,
            host2=args.host2,
            host2_voice=host2_voice,
            host2_notes=args.host2_notes,
            topic=args.topic,
            notes=args.notes,
            duration=args.duration,
            enable_research=not args.no_research,
            model=args.model
        )

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nGeneration cancelled by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
