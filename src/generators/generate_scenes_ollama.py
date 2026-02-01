#!/usr/bin/env python3
"""
Generate scenes using local Ollama LLM (Qwen 3).
Specifically for long books like Animal Farm - generates scenes only, no audio/video.
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.clients.ollama_client import OllamaClient
from src.generators.scene_generator import SceneGenerator


def setup_logging(output_dir: Path) -> logging.Logger:
    """Setup logging to both file and console."""
    log_file = output_dir / "generation.log"

    # Create logger
    logger = logging.getLogger('scene_generation')
    logger.setLevel(logging.INFO)

    # File handler - detailed logs
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    # Console handler - important messages only
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(message)s'))

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def main():
    parser = argparse.ArgumentParser(
        description="Generate scenes from text using local Ollama LLM"
    )

    # Input
    parser.add_argument(
        "--text",
        type=str,
        required=True,
        help="Path to input text file"
    )

    # Output
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory (default: output/<filename>_scenes_<timestamp>)"
    )

    # Generation parameters
    parser.add_argument(
        "--model",
        type=str,
        default="qwen2.5:32b",
        help="Ollama model to use (default: qwen2.5:32b)"
    )

    parser.add_argument(
        "--length",
        type=int,
        default=60,
        help="Target length in minutes (default: 60)"
    )

    parser.add_argument(
        "--art-style",
        type=str,
        default="Watercolor storybook illustration with warm tones, visible brushstrokes, soft lighting",
        help="Art style description"
    )

    parser.add_argument(
        "--narration-style",
        type=str,
        default="warm storytelling voice",
        help="Narration style"
    )

    parser.add_argument(
        "--episode-title",
        type=str,
        help="Episode title (auto-generated if not provided)"
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="Characters per chunk for large texts (default: 5000, targets 10 scenes per chunk)"
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.9,
        help="LLM temperature for creativity (default: 0.9)"
    )

    args = parser.parse_args()

    # Read input text
    print("=" * 80)
    print("OLLAMA SCENE GENERATION")
    print("=" * 80)
    print(f"Model: {args.model}")
    print(f"Input: {args.text}")

    text_path = Path(args.text)
    if not text_path.exists():
        print(f"Error: File not found: {args.text}")
        sys.exit(1)

    with open(text_path, 'r') as f:
        text_content = f.read()

    print(f"Text length: {len(text_content):,} characters")
    print(f"Target length: {args.length} minutes")
    print(f"Estimated scenes: ~{args.length * 10} (at 6 seconds per scene)")
    print()

    # Setup output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = text_path.stem
        output_dir = Path(f"output/{filename}_scenes_{timestamp}")

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")
    print()

    # Initialize Ollama client
    print("Initializing Ollama client...")
    ollama_client = OllamaClient(model=args.model)
    print(f"✓ Client initialized for model: {args.model}")
    print("  (Connection will be tested on first generation request)")
    print()

    # Initialize scene generator with Ollama
    generator = SceneGenerator(
        client=ollama_client,
        model=args.model,
        output_dir=output_dir  # Save intermediate chunks for debugging
    )

    # Override chunk size if needed
    if hasattr(generator, '_generate_scenes_chunked'):
        original_chunk_size = 10000
        # Monkey patch to use custom chunk size
        generator._CHUNK_SIZE = args.chunk_size

    # Generate scenes
    start_time = datetime.now()

    try:
        scenes_data = generator.generate_scenes_from_text(
            text=text_content,
            art_style=args.art_style,
            narrator_style=args.narration_style,
            target_length_minutes=args.length,
            episode_title=args.episode_title,
            use_two_step=True
        )

        # Save scenes
        scenes_file = output_dir / "scenes.json"
        with open(scenes_file, 'w') as f:
            json.dump(scenes_data, f, indent=2)

        # Save metadata
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "model": args.model,
            "source_file": str(text_path),
            "text_length_chars": len(text_content),
            "target_length_minutes": args.length,
            "total_scenes": len(scenes_data['scenes']),
            "art_style": args.art_style,
            "narration_style": args.narration_style,
            "chunk_size": args.chunk_size,
            "temperature": args.temperature,
            "generation_time_seconds": (datetime.now() - start_time).total_seconds()
        }

        metadata_file = output_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Generate report
        report_file = output_dir / "generation_report.txt"
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("SCENE GENERATION REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {metadata['generated_at']}\n")
            f.write(f"Model: {args.model}\n")
            f.write(f"Source: {text_path.name}\n")
            f.write(f"Text length: {len(text_content):,} characters\n")
            f.write(f"Target duration: {args.length} minutes\n")
            f.write(f"Generation time: {metadata['generation_time_seconds']:.1f} seconds\n\n")

            f.write(f"Episode: {scenes_data['episode']['title']}\n")
            f.write(f"Total scenes: {len(scenes_data['scenes'])}\n\n")

            f.write("Scenes:\n")
            f.write("-" * 80 + "\n\n")

            for scene in scenes_data['scenes']:
                f.write(f"{scene['scene_id']}:\n")
                f.write(f"  Sentences: {len(scene['sentences'])}\n")
                for sent in scene['sentences']:
                    f.write(f"    - {sent[:80]}{'...' if len(sent) > 80 else ''}\n")
                f.write(f"  Video: {scene['video_description'][:80]}...\n")
                f.write(f"  Camera: {scene['camera_style']}\n\n")

        print()
        print("=" * 80)
        print("✓ SCENE GENERATION COMPLETE")
        print("=" * 80)
        print(f"Episode: {scenes_data['episode']['title']}")
        print(f"Total scenes: {len(scenes_data['scenes'])}")
        print(f"Generation time: {metadata['generation_time_seconds']:.1f} seconds")
        print()
        print(f"Output files:")
        print(f"  {scenes_file}")
        print(f"  {metadata_file}")
        print(f"  {report_file}")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
